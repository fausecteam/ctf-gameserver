import asyncio
from datetime import datetime, UTC
import logging
import os
import re
import time

import prometheus_client
import psycopg2
from psycopg2 import errorcodes as postgres_errors

from ctf_gameserver.lib import daemon
from ctf_gameserver.lib.args import get_arg_parser_with_db, parse_host_port
from ctf_gameserver.lib.database import transaction_cursor
from ctf_gameserver.lib.metrics import start_metrics_server

from . import database


CHECK_INTERVAL = 60
NETWORK_TIMEOUT = 10


def main():

    arg_parser = get_arg_parser_with_db('CTF Gameserver VPN Status Checker')
    arg_parser.add_argument('--wireguard-ifpattern', type=str, help='Enable on-server Wireguard checks, '
                            '(old-style) Python formatstring for building a team\'s Wireguard interface '
                            'from its net number')
    arg_parser.add_argument('--gateway-ippattern', type=str, help='Enable pings to the teams\' gateways, '
                            '(old-style) Python formatstring for building a team\'s gateway IP from its net '
                            'number')
    arg_parser.add_argument('--demo-ippattern', type=str, help='Enable pings to the teams\' demo Vulnboxes, '
                            'formatstring like --gateway-ippattern')
    arg_parser.add_argument('--demo-serviceport', type=int, help='Enable TCP connection checks to the '
                            'specified port on the teams\' demo Vulnboxes')
    arg_parser.add_argument('--vulnbox-ippattern', type=str, help='Enable pings to the teams\' Vulnboxes, '
                            'formatstring like --gateway-ippattern')
    arg_parser.add_argument('--vulnbox-serviceport', type=int, help='Enable TCP connection checks to the '
                            'specified port on the teams\' Vulnboxes')
    arg_parser.add_argument('--net-numbers-filter-file', type=str, help='Only run checks for teams with '
                            'specific net numbers, file with one net number per line')
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
        database.get_active_teams(db_conn)
        dummy_results = {42: {
            'wireguard_handshake_time': None,
            'gateway_ping_rtt_ms': None,
            'demo_ping_rtt_ms': None,
            'demo_service_ok': False,
            'vulnbox_ping_rtt_ms': None,
            'vulnbox_service_ok': False
        }}
        database.add_results(db_conn, dummy_results, prohibit_changes=True)
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

    net_numbers = None
    if args.net_numbers_filter_file:
        with open(args.net_numbers_filter_file, encoding='ascii') as filter_file:
            net_numbers = set(int(line) for line in filter_file)

    daemon.notify('READY=1')

    asyncio.run(main_loop(db_conn, metrics, args.wireguard_ifpattern, args.gateway_ippattern,
                          args.demo_ippattern, args.demo_serviceport, args.vulnbox_ippattern,
                          args.vulnbox_serviceport, net_numbers))

    return os.EX_OK


def make_metrics(registry=prometheus_client.REGISTRY):

    metrics = {}
    metric_prefix = 'ctf_vpnstatus_'

    gauges = [
        ('start_timestamp', '(Unix) timestamp when the process was started', []),
        ('up_count', 'Teams with a successful ping/connection/handshake', ['kind']),
        ('check_duration_seconds', 'Time spent running all latest checks for all teams', [])
    ]
    for name, doc, labels in gauges:
        metrics[name] = prometheus_client.Gauge(metric_prefix+name, doc, labels, registry=registry)

    histograms = [
        ('ping_milliseconds', 'Ping RTT for all teams', ['target'],
         (1, 10, 50, 100, 200, 500, 1000, float('inf')))
    ]
    for name, doc, labels, buckets in histograms:
        metrics[name] = prometheus_client.Histogram(metric_prefix+name, doc, labels, buckets=buckets,
                                                    registry=registry)

    return metrics


async def main_loop(db_conn, metrics, wireguard_if_pattern=None, gateway_ip_pattern=None,
                    demo_ip_pattern=None, demo_service_port=None, vulnbox_ip_pattern=None,
                    vulnbox_service_port=None, team_net_numbers=None):
    """
    Continuously runs all different checks at the check interval and adds the results to the database.
    """

    while True:
        start_time = time.monotonic()

        await loop_step(db_conn, metrics, wireguard_if_pattern, gateway_ip_pattern, demo_ip_pattern,
                        demo_service_port, vulnbox_ip_pattern, vulnbox_service_port, team_net_numbers)

        sleep_duration = CHECK_INTERVAL - (time.monotonic() - start_time)
        if sleep_duration < 0:
            logging.warning('Check interval exceeded')
        else:
            logging.info('Sleeping for %f seconds', sleep_duration)
            await asyncio.sleep(sleep_duration)


async def loop_step(db_conn, metrics, wireguard_if_pattern=None, gateway_ip_pattern=None,
                    demo_ip_pattern=None, demo_service_port=None, vulnbox_ip_pattern=None,
                    vulnbox_service_port=None, team_net_numbers=None):

    start_time = time.monotonic()
    teams = database.get_active_teams(db_conn)

    if team_net_numbers is not None:
        teams = [t for t in teams if t[1] in team_net_numbers]

    checks = []
    if wireguard_if_pattern:
        checks.append(check_wireguard(wireguard_if_pattern, teams))
    if gateway_ip_pattern:
        checks.append(check_pings(gateway_ip_pattern, teams))
    if demo_ip_pattern:
        checks.append(check_pings(demo_ip_pattern, teams))
    if demo_ip_pattern and demo_service_port:
        checks.append(check_tcp_connects(demo_ip_pattern, demo_service_port, teams))
    if vulnbox_ip_pattern:
        checks.append(check_pings(vulnbox_ip_pattern, teams))
    if vulnbox_ip_pattern and vulnbox_service_port:
        checks.append(check_tcp_connects(vulnbox_ip_pattern, vulnbox_service_port, teams))

    logging.info('Starting %d checks for %d teams', len(checks), len(teams))
    check_results = await asyncio.gather(*checks, return_exceptions=True)

    results = {
        t[0]: {
            'wireguard_handshake_time': None,
            'gateway_ping_rtt_ms': None,
            'demo_ping_rtt_ms': None,
            'demo_service_ok': False,
            'vulnbox_ping_rtt_ms': None,
            'vulnbox_service_ok': False
        } for t in teams
    }

    def update_results(key):
        nonlocal check_results
        up_count = 0

        if isinstance(check_results[0], Exception):
            logging.error('Exception during status check:', exc_info=check_results[0])
        else:
            for team_id, check_result in check_results[0].items():
                results[team_id][key] = check_result

                # We have to check for identity here because 0 is False but a valid "up" value
                if check_result is not False and check_result is not None:
                    up_count += 1
                if key.endswith('_ping_rtt_ms') and check_result is not None:
                    metric_target = key.removesuffix('_ping_rtt_ms')
                    metrics['ping_milliseconds'].labels(metric_target).observe(check_result)
        metric_kind = key.removesuffix('_time').removesuffix('_rtt_ms').removesuffix('_ok')
        metrics['up_count'].labels(metric_kind).set(up_count)

        check_results = check_results[1:]

    if wireguard_if_pattern:
        update_results('wireguard_handshake_time')
    if gateway_ip_pattern:
        update_results('gateway_ping_rtt_ms')
    if demo_ip_pattern:
        update_results('demo_ping_rtt_ms')
    if demo_ip_pattern and demo_service_port:
        update_results('demo_service_ok')
    if vulnbox_ip_pattern:
        update_results('vulnbox_ping_rtt_ms')
    if vulnbox_ip_pattern and vulnbox_service_port:
        update_results('vulnbox_service_ok')

    database.add_results(db_conn, results)
    logging.info('Added results for %d teams to database', len(results))

    run_duration = time.monotonic() - start_time
    metrics['check_duration_seconds'].set(run_duration)


async def check_wireguard(if_pattern, teams):

    teams_map = {if_pattern % team[1]: team[0] for team in teams}
    results = {}

    cmd = ['sudo', '--non-interactive', '--', '/usr/bin/wg', 'show', 'all', 'latest-handshakes']
    proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=None)

    while data := await proc.stdout.readline():
        line = data.decode('ascii').rstrip()
        interface, _, handshake_timestamp = line.split('\t')

        if interface not in teams_map:
            continue

        if handshake_timestamp == '0':
            # No handshake yet
            handshake_time = None
        else:
            handshake_time = datetime.fromtimestamp(int(handshake_timestamp), UTC)
        results[teams_map[interface]] = handshake_time

    await proc.wait()

    if proc.returncode == os.EX_OK:
        return results
    else:
        logging.error('"%s" call failed with exit code %d', ' '.join(cmd), proc.returncode)
        return {}


async def check_tcp_connects(ip_pattern, port, teams):

    async def check_connect(ip, port):
        async def connect():
            _, writer = await asyncio.open_connection(ip, port)
            writer.close()
            await writer.wait_closed()
            return True
        try:
            return await asyncio.wait_for(connect(), timeout=NETWORK_TIMEOUT)
        # TimeoutError is different from asyncio.TimeoutError in Python < 3.11
        except (OSError, TimeoutError, asyncio.TimeoutError):
            return False

    checks = [check_connect(ip_pattern % team[1], port) for team in teams]
    results = await asyncio.gather(*checks)

    return {team[0]: result for team, result in zip(teams, results)}


async def check_pings(ip_pattern, teams):

    async def ping(ip):
        cmd = ['ping', '-W', str(NETWORK_TIMEOUT), '-c', '1', '-n', ip]
        # `stderr=None` inherits the parents stderr, "sendmsg: Destination address required" messages here
        # result from the WireGuard interface having no active peer and returning EDESTADDRREQ
        proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=None)

        rtt_re = re.compile(r'^rtt min/avg/max/mdev = ([0-9.]+)/[0-9.]+/[0-9.]+/[0-9.-]+ ms$')
        rtt = None

        while data := await proc.stdout.readline():
            line = data.decode('ascii').rstrip()
            match = rtt_re.search(line)
            if match:
                rtt = round(float(match.group(1)))

        await proc.wait()

        if proc.returncode == 0:
            if rtt is None:
                logging.error('"%s" call returned 0, but could not parse result', ' '.join(cmd))
            if rtt > NETWORK_TIMEOUT * 1000:
                # RTT values are unreliable because time is stored in the ICMP data field, which is
                # controlled by the ping target in Reply packets:
                #   https://stackoverflow.com/a/71461124/1792200
                #   https://datatracker.ietf.org/doc/html/rfc4443#section-4.2
                # We once saw some interesting things here:
                #   rtt min/avg/max/mdev =
                #   700000000777036.385/700000000777036.416/700000000777036.385/-9223372036854775.-808 ms
                logging.warning('"%s" call returned bogus RTT: %d', ' '.join(cmd), rtt)
                # Safe max value of Django PositiveIntegerField
                return 2147483647
            return rtt
        elif proc.returncode == 1:
            # No reply received
            return None
        else:
            logging.error('"%s" call failed with exit code %d', ' '.join(cmd), proc.returncode)
            return None

    checks = [ping(ip_pattern % team[1]) for team in teams]
    results = await asyncio.gather(*checks)

    return {team[0]: result for team, result in zip(teams, results)}
