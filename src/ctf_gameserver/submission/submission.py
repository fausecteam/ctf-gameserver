import asyncio
import base64
from binascii import Error as BinasciiError
import datetime
import logging
import os
import re
import sqlite3
import time

import prometheus_client
import psycopg2
from psycopg2 import errorcodes as postgres_errors

from ctf_gameserver.lib import daemon
import ctf_gameserver.lib.flag as flag_lib
from ctf_gameserver.lib.args import get_arg_parser_with_db, parse_host_port
from ctf_gameserver.lib.database import transaction_cursor
from ctf_gameserver.lib.exceptions import DBDataError
from ctf_gameserver.lib.metrics import start_metrics_server

from . import database


TIMEOUT_SECONDS = 300


def main():

    arg_parser = get_arg_parser_with_db('CTF Gameserver Submission Server')
    arg_parser.add_argument('--listen', default="localhost:6666",
                            help='Address and port to listen on ("<host>:<port>")')
    arg_parser.add_argument('--flagsecret', required=True,
                            help='Base64 string used as secret in flag generation')
    arg_parser.add_argument('--teamregex', required=True,
                            help='Python regex (with match group) to extract team net number from '
                            'connecting IP address')
    arg_parser.add_argument('--metrics-listen', help='Expose Prometheus metrics via HTTP ("<host>:<port>")')

    args = arg_parser.parse_args()

    logging.basicConfig(format='[%(levelname)s] %(message)s')
    numeric_loglevel = getattr(logging, args.loglevel.upper())
    logging.getLogger().setLevel(numeric_loglevel)

    try:
        listen_host, listen_port, _ = parse_host_port(args.listen)
    except ValueError:
        logging.error('Listen address needs to be specified as "<host>:<port>"')
        return os.EX_USAGE

    try:
        flag_secret = base64.b64decode(args.flagsecret)
    except BinasciiError:
        logging.error('Flag secret must be valid Base64')
        return os.EX_USAGE

    try:
        team_regex = re.compile(args.teamregex)
    except re.error:
        logging.error('Team regex must be a valid regular expression')
        return os.EX_USAGE
    if team_regex.groups != 1:
        logging.error('Team regex must contain one match group')
        return os.EX_USAGE

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
            database.get_static_info(db_conn)
            database.get_dynamic_info(db_conn)
        except DBDataError as e:
            logging.warning('Invalid database state: %s', e)

        database.team_is_nop(db_conn, 1)
        database.add_capture(db_conn, 2147483647, 1, prohibit_changes=True, fake_team_id=42, fake_tick=1)
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

    metrics = make_metrics()
    metrics['start_timestamp'].set_to_current_time()

    daemon.notify('READY=1')

    while True:
        try:
            competition_name, flag_prefix = database.get_static_info(db_conn)
        except DBDataError as e:
            logging.warning('Invalid database state, sleeping for 60 seconds: %s', e)
            time.sleep(60)
        else:
            break

    asyncio.run(serve(listen_host, listen_port, db_conn, {
        'flag_secret': flag_secret,
        'team_regex': team_regex,
        'competition_name': competition_name,
        'flag_prefix': flag_prefix,
        'metrics': metrics
    }))

    return os.EX_OK


def make_metrics(registry=prometheus_client.REGISTRY):

    metrics = {}
    metric_prefix = 'ctf_submission_'

    counters = [
        ('connections', 'Total number of connections', ['team_net_no']),
        ('flags_ok', 'Number of submitted valid flags', ['team_net_no']),
        ('flags_dup', 'Number of submitted duplicate flags', ['team_net_no']),
        ('flags_old', 'Number of submitted expired flags', ['team_net_no']),
        ('flags_own', 'Number of submitted own flags', ['team_net_no']),
        ('flags_inv', 'Number of submitted invalid flags', ['team_net_no']),
        ('flags_err', 'Number of submitted flags which resulted in an error', ['team_net_no']),
        ('server_kills', 'Number of times the server was force-restarted due to fatal errors', []),
        ('unhandled_exceptions', 'Number of unexpected exceptions in client connections', [])
    ]
    for name, doc, labels in counters:
        metrics[name] = prometheus_client.Counter(metric_prefix+name, doc, labels, registry=registry)

    gauges = [
        ('start_timestamp', '(Unix) timestamp when the process was started', []),
        ('open_connections', 'Number of currently open connections', ['team_net_no'])
    ]
    for name, doc, labels in gauges:
        metrics[name] = prometheus_client.Gauge(metric_prefix+name, doc, labels, registry=registry)

    histograms = [
        ('submission_duration', 'Time spent processing a single flag in seconds', [])
    ]
    for name, doc, labels in histograms:
        # The default buckets seem appropriate for our use case
        metrics[name] = prometheus_client.Histogram(metric_prefix+name, doc, labels, registry=registry)

    return metrics


async def serve(host, port, db_conn, params):

    async def wrapper(reader, writer):
        metrics = params['metrics']
        client_addr = writer.get_extra_info('peername')[0]

        try:
            await handle_connection(reader, writer, db_conn, params)
        except KillServerException:
            logging.error('Encountered fatal error, exiting')
            metrics['server_kills'].inc()
            # pylint: disable=protected-access
            os._exit(os.EX_IOERR)
        except ConnectionError:
            logging.warning('[%s]: Client connection error, closing the connection', client_addr)
            writer.close()
        except:    # noqa, pylint: disable=bare-except
            logging.exception('[%s]: Exception in client connection, closing the connection:', client_addr)
            metrics['unhandled_exceptions'].inc()
            writer.close()

    logging.info('Starting server on %s:%d', host, port)
    server = await asyncio.start_server(wrapper, host, port)

    async with server:
        await server.serve_forever()


async def handle_connection(reader, writer, db_conn, params):
    """
    Coroutine managing the protocol flow with a single client.
    """

    metrics = params['metrics']
    client_addr = writer.get_extra_info('peername')[0]

    try:
        client_net_no = _match_net_number(params['team_regex'], client_addr)
    except ValueError:
        logging.error('[%s]: Could not match client address with team, closing the connection', client_addr)
        metrics['connections'].labels(-1).inc()
        writer.write(b'Error: Could not match your IP address with a team\n')
        writer.close()
        return

    metrics['connections'].labels(client_net_no).inc()
    metrics['open_connections'].labels(client_net_no).inc()

    try:
        await handle_team_connection(reader, writer, db_conn, params, client_addr, client_net_no)
    finally:
        metrics['open_connections'].labels(client_net_no).dec()


async def handle_team_connection(reader, writer, db_conn, params, client_addr, client_net_no):
    """
    Continuation of handle_connection() for when the net number is already known.
    Communication with the database happens synchronously because psycopg2 does not support asyncio. We do
    not think that is a practical issue.
    """

    metrics = params['metrics']

    def log(level_name, message, *args):
        level = logging.getLevelName(level_name)
        logging.log(level, '%d [%s]: ' + message, client_net_no, client_addr, *args)

    log('INFO', 'Accepted connection from %s (team net number %d)', client_addr, client_net_no)

    writer.write(f'{params["competition_name"]} Flag Submission Server\n'.encode('utf-8'))
    writer.write(b'One flag per line please!\n\n')

    line_start_time = None

    while True:
        # Record duration of the previous loop iteration
        if line_start_time is not None:
            duration_seconds = (time.monotonic_ns() - line_start_time) / 10**9
            metrics['submission_duration'].observe(duration_seconds)

        # Prevent asyncio buffer of unbounded size (i.e. memory leak) if the client never reads our responses
        try:
            await asyncio.wait_for(writer.drain(), TIMEOUT_SECONDS)
        except:    # noqa, pylint: disable=bare-except
            log('INFO', 'Write timeout expired')
            break

        try:
            line = await asyncio.wait_for(reader.readline(), TIMEOUT_SECONDS)
        except asyncio.TimeoutError:
            log('INFO', 'Read timeout expired')
            break

        line_start_time = time.monotonic_ns()

        if not line.endswith(b'\n'):
            # EOF
            break
        raw_flag = line[:-1]

        try:
            flag = raw_flag.decode('ascii')
        except UnicodeDecodeError:
            writer.write(raw_flag + b' INV Invalid flag\n')
            log('INFO', 'Flag %s rejected due to bad encoding', repr(raw_flag))
            metrics['flags_inv'].labels(client_net_no).inc()
            continue

        try:
            flag_id, protecting_net_no = flag_lib.verify(flag, params['flag_secret'], params['flag_prefix'])
        except flag_lib.InvalidFlagFormat:
            writer.write(raw_flag + b' INV Invalid flag\n')
            log('INFO', 'Flag %s rejected due to invalid format', repr(flag))
            metrics['flags_inv'].labels(client_net_no).inc()
            continue
        except flag_lib.InvalidFlagMAC:
            writer.write(raw_flag + b' INV Invalid flag\n')
            log('INFO', 'Flag %s rejected due to invalid MAC', repr(flag))
            metrics['flags_inv'].labels(client_net_no).inc()
            continue
        except flag_lib.FlagExpired as e:
            writer.write(raw_flag + b' OLD Flag has expired\n')
            log('INFO', 'Flag %s rejected because it has expired since %s', repr(flag),
                e.expiration_time.isoformat())
            metrics['flags_old'].labels(client_net_no).inc()
            continue

        if protecting_net_no == client_net_no:
            writer.write(raw_flag + b' OWN You cannot submit your own flag\n')
            log('INFO', 'Flag %s rejected because it is protected by submitting team', repr(flag))
            metrics['flags_own'].labels(client_net_no).inc()
            continue

        try:
            now = datetime.datetime.now(datetime.timezone.utc)
            start, end = database.get_dynamic_info(db_conn)
            if now < start:
                writer.write(raw_flag + b' ERR Competition has not even started yet\n')
                log('INFO', 'Flag %s rejected because competition has not started', repr(flag))
                metrics['flags_err'].labels(client_net_no).inc()
                continue
            if now >= end:
                writer.write(raw_flag + b' ERR Competition is over\n')
                log('INFO', 'Flag %s rejected because competition is over', repr(flag))
                metrics['flags_err'].labels(client_net_no).inc()
                continue

            if database.team_is_nop(db_conn, protecting_net_no):
                writer.write(raw_flag + b' INV You cannot submit flags of a NOP team\n')
                log('INFO', 'Flag %s rejected because it is protected by a NOP team', repr(flag))
                metrics['flags_inv'].labels(client_net_no).inc()
                continue

            try:
                database.add_capture(db_conn, flag_id, client_net_no)
                writer.write(raw_flag + b' OK\n')
                log('INFO', 'Flag %s accepted', repr(flag))
                metrics['flags_ok'].labels(client_net_no).inc()
            except database.DuplicateCapture:
                writer.write(raw_flag + b' DUP You already submitted this flag\n')
                log('INFO', 'Flag %s rejected because it has already been submitted before', repr(flag))
                metrics['flags_dup'].labels(client_net_no).inc()
            except database.TeamNotExisting:
                writer.write(raw_flag + b' ERR Could not find team\n')
                log('WARNING', 'Flag %s: Could not find team for net number %d in database', repr(flag),
                    client_net_no)
                metrics['flags_err'].labels(client_net_no).inc()
        except (psycopg2.Error, sqlite3.Error) as e:
            logging.exception('Database error:')
            raise KillServerException() from e

    log('INFO', 'Closing connection')
    writer.close()


def _match_net_number(regex, addr):
    """
    Determines the net number for an address using the given regex. Implemented as separate function to
    enable mocking in test cases.
    """

    match = regex.search(addr)
    if not match:
        raise ValueError()

    return int(match.group(1))


class KillServerException(Exception):
    """
    Indicates that a fatal error occured and the server shall be stopped (and then usually get restarted
    through systemd).
    """
