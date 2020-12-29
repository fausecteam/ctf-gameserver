import datetime
import logging
import time
import os

import prometheus_client
import prometheus_client.core
import psycopg2
from psycopg2 import errorcodes as postgres_errors

from ctf_gameserver.lib import daemon
from ctf_gameserver.lib.args import get_arg_parser_with_db, parse_host_port
from ctf_gameserver.lib.database import transaction_cursor
from ctf_gameserver.lib.exceptions import DBDataError
from ctf_gameserver.lib.metrics import start_metrics_server

from . import database


def main():

    arg_parser = get_arg_parser_with_db('CTF Gameserver Controller')
    arg_parser.add_argument('--nonstop', action='store_true', help='Use current time as start time and '
                            'ignore CTF end time from the database. Useful for testing checkers.')
    arg_parser.add_argument('--metrics-listen', help='Expose Prometheus metrics via HTTP ("<host>:<port>")')

    args = arg_parser.parse_args()

    logging.basicConfig(format='[%(levelname)s] %(message)s')
    numeric_loglevel = getattr(logging, args.loglevel.upper())
    logging.getLogger().setLevel(numeric_loglevel)

    try:
        db_conn = psycopg2.connect(host=args.dbhost, database=args.dbname, user=args.dbuser,
                                   password=args.dbpassword)
    except psycopg2.OperationalError as e:
        logging.error('Could not establish database connection: %s', e)
        return os.EX_UNAVAILABLE
    logging.info('Established database connection')

    # Keep our mental model easy by always using (timezone-aware) UTC for dates and times
    with transaction_cursor(db_conn) as cursor:
        cursor.execute('SET TIME ZONE "UTC"')

    # Check database grants
    try:
        try:
            database.get_control_info(db_conn, prohibit_changes=True)
        except DBDataError as e:
            logging.warning('Invalid database state: %s', e)

        database.increase_tick(db_conn, prohibit_changes=True)
    except psycopg2.ProgrammingError as e:
        if e.pgcode == postgres_errors.INSUFFICIENT_PRIVILEGE:
            # Log full exception because only the backtrace will tell which kind of permission is missing
            logging.exception('Missing database permissions:')
            return os.EX_NOPERM
        else:
            raise

    if args.metrics_listen is not None:
        try:
            metrics_host, metrics_port, metrics_family = parse_host_port(args.metrics_listen)
        except ValueError:
            logging.error('Metrics listen address needs to be specified as "<host>:<port>"')
            return os.EX_USAGE

        start_metrics_server(metrics_host, metrics_port, metrics_family)

    metrics = make_metrics(db_conn)
    metrics['start_timestamp'].set(time.time())

    daemon.notify('READY=1')

    while True:
        main_loop_step(db_conn, metrics, args.nonstop)


def make_metrics(db_conn, registry=prometheus_client.REGISTRY):

    metrics = {}
    metric_prefix = 'ctf_controller_'

    gauges = [
        ('start_timestamp', '(Unix) timestamp when the process was started', []),
        ('current_tick', 'The current tick', [])
    ]
    for name, doc, labels in gauges:
        metrics[name] = prometheus_client.Gauge(metric_prefix+name, doc, labels, registry=registry)

    histograms = [
        ('tick_change_delay_seconds', 'Differences between supposed and actual tick change times', [],
         (1, 3, 5, 10, 30, 60, float('inf')))
    ]
    for name, doc, labels, buckets in histograms:
        metrics[name] = prometheus_client.Histogram(metric_prefix+name, doc, labels, buckets=buckets,
                                                    registry=registry)

    class DatabaseCollector:
        def collect(self):
            exploiting_teams = prometheus_client.core.CounterMetricFamily(
                metric_prefix+'exploiting_teams',
                'Number of teams that submitted at least one flag',
                labels=['service']
            )
            is_exploited = prometheus_client.core.GaugeMetricFamily(
                metric_prefix+'is_exploited',
                'Whether at least one team submitted at least one flag',
                labels=['service']
            )
            for service, count in database.get_exploiting_teams_counts(db_conn).items():
                exploiting_teams.add_metric([service], count)
                is_exploited.add_metric([service], int(count > 0))
            yield exploiting_teams
            yield is_exploited

            unplaced_flags = prometheus_client.core.CounterMetricFamily(
                metric_prefix+'unplaced_flags',
                'Flags whose placement was not started by a checker',
                labels=['service', 'ticks']
            )
            for service, count in database.get_unplaced_flags_counts_cur(db_conn).items():
                unplaced_flags.add_metric([service, 'cur'], count)
            for service, count in database.get_unplaced_flags_counts_old(db_conn).items():
                unplaced_flags.add_metric([service, 'old'], count)
            yield unplaced_flags

            incomplete_flags = prometheus_client.core.CounterMetricFamily(
                metric_prefix+'incomplete_flags',
                'Flags whose placement by a checker was started, but has not finished',
                labels=['service', 'ticks']
            )
            for service, count in database.get_incomplete_flags_counts_cur(db_conn).items():
                incomplete_flags.add_metric([service, 'cur'], count)
            for service, count in database.get_incomplete_flags_counts_old(db_conn).items():
                incomplete_flags.add_metric([service, 'old'], count)
            yield incomplete_flags

    registry.register(DatabaseCollector())

    return metrics


def main_loop_step(db_conn, metrics, nonstop):

    def sleep(duration):
        logging.info('Sleeping for %d seconds', duration)
        time.sleep(duration)

    try:
        control_info = database.get_control_info(db_conn)
    except DBDataError as e:
        logging.warning('Invalid database state: %s', e)
        sleep(60)
        return

    metrics['current_tick'].set(control_info['current_tick'])

    # These fields are allowed to be NULL
    if control_info['start'] is None or control_info['end'] is None:
        logging.warning('Competition start and end time must be configured in the database')
        sleep(60)
        return

    sleep_seconds = get_sleep_seconds(control_info, metrics)
    # Do not wait for too long, especially before the competition starts, to avoid missing changes in the
    # database
    sleep_seconds = min(sleep_seconds, 60)
    sleep(sleep_seconds)

    # Fetch fresh info from the database
    control_info = database.get_control_info(db_conn)
    # Get timezone-aware datetime object with UTC timezone
    now = datetime.datetime.now(datetime.timezone.utc)

    if ((control_info['end'] - control_info['start']).total_seconds() % control_info['tick_duration']) != 0:
        logging.warning('Competition duration not divisible by tick duration, strange things might happen')

    if (not nonstop) and (now > control_info['end']):
        # Do not stop the program because a daemon might get restarted if it exits
        # Prevent a busy loop in case we have not slept above as the hypothetic next tick would be overdue
        logging.info('Competition is already over')
        sleep(60)
        return

    # Check if we really need to increase the tick because of the capping to 60 seconds from above
    if get_sleep_seconds(control_info, metrics) <= 0:
        logging.info('After tick %d, increasing tick to the next one', control_info['current_tick'])
        database.increase_tick(db_conn)
        database.update_scoring(db_conn)


def get_sleep_seconds(control_info, metrics, now=None):
    """
    Returns the number of seconds until the next tick starts.
    """

    if now is None:
        now = datetime.datetime.now(datetime.timezone.utc)

    next_tick_start_offset = (control_info['current_tick'] + 1) * control_info['tick_duration']
    next_tick_start = control_info['start'] + datetime.timedelta(seconds=next_tick_start_offset)
    until_next_tick = next_tick_start - now
    until_next_tick_secs = until_next_tick.total_seconds()

    if until_next_tick_secs <= 0:
        metrics['tick_change_delay_seconds'].observe(-1 * until_next_tick_secs)

    return max(until_next_tick_secs, 0)
