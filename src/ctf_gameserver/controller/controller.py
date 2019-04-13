import datetime
import logging
import time
import os

import psycopg2
from psycopg2 import errorcodes as postgres_errors

from ctf_gameserver.lib import daemon
from ctf_gameserver.lib.args import get_arg_parser_with_db
from ctf_gameserver.lib.database import transaction_cursor
from ctf_gameserver.lib.exceptions import DBDataError

from . import database


def main():

    arg_parser = get_arg_parser_with_db('CTF Gameserver Controller')
    arg_parser.add_argument('--nonstop', action='store_true', help='Use current time as start time and '
                            'ignore CTF end time from the database. Useful for testing checkers.')

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
        database.get_control_info(db_conn, prohibit_changes=True)
        database.increase_tick(db_conn, prohibit_changes=True)
    except psycopg2.ProgrammingError as e:
        if e.pgcode == postgres_errors.INSUFFICIENT_PRIVILEGE:
            # Log full exception because only the backtrace will tell which kind of permission is missing
            logging.exception('Missing database permissions:')
            return os.EX_NOPERM
        else:
            raise
    except DBDataError as e:
        logging.error('Invalid database state: %s', e)
        return os.EX_DATAERR

    daemon.notify('READY=1')

    while True:
        main_loop_step(db_conn, args.nonstop)


def main_loop_step(db_conn, nonstop):

    def sleep(duration):
        logging.info('Sleeping for %d seconds', duration)
        time.sleep(duration)

    control_info = database.get_control_info(db_conn)

    # These fields are allowed to be NULL
    if control_info['start'] is None or control_info['end'] is None:
        logging.warning('Competition start and end time must be configured in the database')
        sleep(60)
        return

    sleep_seconds = get_sleep_seconds(control_info)
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
    if get_sleep_seconds(control_info) <= 0:
        logging.info('After tick %d, increasing tick to the next one', control_info['current_tick'])
        database.increase_tick(db_conn)


def get_sleep_seconds(control_info, now=None):
    """
    Returns the number of seconds until the next tick starts.
    """

    if now is None:
        now = datetime.datetime.now(datetime.timezone.utc)

    next_tick_start_offset = (control_info['current_tick'] + 1) * control_info['tick_duration']
    next_tick_start = control_info['start'] + datetime.timedelta(seconds=next_tick_start_offset)
    until_next_tick = next_tick_start - now

    return max(until_next_tick.total_seconds(), 0)
