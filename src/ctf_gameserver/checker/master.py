import base64
import datetime
import logging
import math
import multiprocessing
import os
import signal
import time

import psycopg2
from psycopg2 import errorcodes as postgres_errors

from ctf_gameserver.lib.args import get_arg_parser_with_db, parse_host_port
from ctf_gameserver.lib import daemon
from ctf_gameserver.lib.checkresult import CheckResult, STATUS_TIMEOUT
from ctf_gameserver.lib.database import transaction_cursor
from ctf_gameserver.lib.exceptions import DBDataError
import ctf_gameserver.lib.flag as flag_lib

from . import database, metrics
from .supervisor import RunnerSupervisor
from .supervisor import ACTION_FLAG, ACTION_FLAGID, ACTION_LOAD, ACTION_STORE, ACTION_RESULT


def main():

    arg_parser = get_arg_parser_with_db('CTF Gameserver Checker Master')
    arg_parser.add_argument('--ippattern', type=str, required=True,
                            help='(Old-style) Python formatstring for building the IP to connect to')
    arg_parser.add_argument('--flagsecret', type=str, required=True,
                            help='Base64 string used as secret in flag generation')
    arg_parser.add_argument('--metrics-listen', type=str, help='Expose Prometheus metrics via HTTP '
                            '("<host>:<port>")')

    group = arg_parser.add_argument_group('check', 'Check parameters')
    group.add_argument('--service', type=str, required=True,
                       help='Slug of the service')
    group.add_argument('--checkerscript', type=str, required=True,
                       help='Path of the Checker Script')
    group.add_argument('--sudouser', type=str, help=' User to excute the Checker Scripts as, will be passed '
                       'to `sudo -u`')
    group.add_argument('--stddeviations', type=float, default=2.0,
                       help='Consider past runtimes within this number of standard deviations when '
                       'estimating Checker Script runtime (default: 2)')
    group.add_argument('--checkercount', type=int, required=True,
                       help='Number of Checker Masters running for this service')
    group.add_argument('--interval', type=float, required=True,
                       help='Time between launching batches of Checker Scripts in seconds')

    group = arg_parser.add_argument_group('logging', 'Checker Script logging')
    group.add_argument('--journald', action='store_true', help='Log Checker Script messages to journald')
    group.add_argument('--gelf-server', help='Log Checker Script messages to the specified GELF (Graylog) '
                       'server ("<host>:<port>")')

    args = arg_parser.parse_args()

    logging.basicConfig(format='[%(levelname)s] %(message)s [%(name)s]')
    numeric_loglevel = getattr(logging, args.loglevel.upper())
    logging.getLogger().setLevel(numeric_loglevel)

    if args.interval < 3:
        logging.error('`--interval` must be at least 3 seconds')
        return os.EX_USAGE

    logging_params = {}

    # Configure logging
    if args.journald:
        try:
            # pylint: disable=import-outside-toplevel,unused-import,import-error
            from systemd.journal import JournalHandler
        except ImportError:
            logging.error('systemd module is required for journald logging')
            return os.EX_USAGE
        logging_params['journald'] = True

    if args.gelf_server is not None:
        try:
            # pylint: disable=import-outside-toplevel,unused-import,import-error
            import graypy
        except ImportError:
            logging.error('graypy module is required for GELF logging')
            return os.EX_USAGE
        try:
            gelf_host, gelf_port, gelf_family = parse_host_port(args.gelf_server)
        except ValueError:
            logging.error('GELF server needs to be specified as "<host>:<port>"')
            return os.EX_USAGE
        logging_params['gelf'] = {'host': gelf_host, 'port': gelf_port, 'family': gelf_family}

    # Configure metrics
    if args.metrics_listen is not None:
        try:
            metrics_host, metrics_port, metrics_family = parse_host_port(args.metrics_listen)
        except ValueError:
            logging.error('Metrics listen address needs to be specified as "<host>:<port>"')
            return os.EX_USAGE

        metrics_queue = multiprocessing.Queue()
        metrics_recv, metrics_send = multiprocessing.Pipe()
        metrics_collector_process = multiprocessing.Process(
            target=metrics.run_collector,
            args=(args.service, metrics.checker_metrics_factory, metrics_queue, metrics_send)
        )
        # Terminate the process when the parent process exits
        metrics_collector_process.daemon = True
        metrics_collector_process.start()
        logging.info('Started metrics collector process')
        metrics_server_process = multiprocessing.Process(
            target=metrics.run_http_server,
            args=(metrics_host, metrics_port, metrics_family, metrics_queue, metrics_recv)
        )
        metrics_server_process.daemon = True
        metrics_server_process.start()
        logging.info('Started metrics HTTP server process')

        metrics.set(metrics_queue, 'interval_length_seconds', args.interval)
        metrics.set(metrics_queue, 'start_timestamp', time.time())
    else:
        metrics_queue = metrics.DummyQueue()

    flag_secret = base64.b64decode(args.flagsecret)

    # Connect to databases
    try:
        db_conn = psycopg2.connect(host=args.dbhost, database=args.dbname, user=args.dbuser,
                                   password=args.dbpassword)
    except psycopg2.OperationalError as e:
        logging.error('Could not establish connection to database: %s', e)
        return os.EX_UNAVAILABLE
    logging.info('Established connection to database')

    # Keep our mental model easy by always using (timezone-aware) UTC for dates and times
    with transaction_cursor(db_conn) as cursor:
        cursor.execute('SET TIME ZONE "UTC"')

    # Check database grants
    try:
        try:
            database.get_control_info(db_conn, prohibit_changes=True)
        except DBDataError as e:
            logging.warning('Invalid database state: %s', e)
        try:
            service_id = database.get_service_attributes(db_conn, args.service,
                                                         prohibit_changes=True)['id']
            database.get_service_margin(db_conn, args.service, prohibit_changes=True)
        except DBDataError as e:
            logging.warning('Invalid database state: %s', e)
            service_id = 1337    # Use dummy value for subsequent grant checks
        try:
            database.get_current_tick(db_conn, prohibit_changes=True)
        except DBDataError as e:
            logging.warning('Invalid database state: %s', e)

        database.get_task_count(db_conn, service_id, prohibit_changes=True)
        database.get_new_tasks(db_conn, service_id, 1, prohibit_changes=True)
        database.get_flag_id(db_conn, service_id, 1, 1, prohibit_changes=True, fake_flag_id=42)
        database.commit_result(db_conn, service_id, 1, 2147483647, 0, prohibit_changes=True, fake_team_id=1)
        database.set_flagid(db_conn, service_id, 1, 0, 'id', prohibit_changes=True, fake_team_id=1)
        database.load_state(db_conn, service_id, 1, 'key', prohibit_changes=True)
        database.store_state(db_conn, service_id, 1, 'key', 'data', prohibit_changes=True, fake_team_id=1)
    except psycopg2.ProgrammingError as e:
        if e.pgcode == postgres_errors.INSUFFICIENT_PRIVILEGE:
            # Log full exception because only the backtrace will tell which kind of permission is missing
            logging.exception('Missing database permissions:')
            return os.EX_NOPERM
        else:
            raise

    daemon.notify('READY=1')

    while True:
        try:
            master_loop = MasterLoop(db_conn, args.service, args.checkerscript, args.sudouser,
                                     args.stddeviations, args.checkercount, args.interval, args.ippattern,
                                     flag_secret, logging_params, metrics_queue)
            break
        except DBDataError as e:
            logging.warning('Waiting for valid database state: %s', e)
            time.sleep(60)

    # Graceful shutdown to prevent loss of check results
    def sigterm_handler(_, __):
        logging.info('Shutting down, waiting for %d Checker Scripts to finish',
                     master_loop.get_running_script_count())
        master_loop.shutting_down = True
    signal.signal(signal.SIGTERM, sigterm_handler)

    try:
        while True:
            master_loop.step()
            if master_loop.shutting_down and master_loop.get_running_script_count() == 0:
                break
    except:    # noqa, pylint: disable=bare-except
        logging.exception('Aborting due to unexpected error:')
        master_loop.supervisor.terminate_runners()
        return os.EX_SOFTWARE

    return os.EX_OK


class MasterLoop:

    def __init__(self, db_conn, service_slug, checker_script, sudo_user, std_dev_count, checker_count,
                 interval, ip_pattern, flag_secret, logging_params, metrics_queue):
        self.db_conn = db_conn
        self.checker_script = checker_script
        self.sudo_user = sudo_user
        self.std_dev_count = std_dev_count
        self.checker_count = checker_count
        self.interval = interval
        self.ip_pattern = ip_pattern
        self.flag_secret = flag_secret
        self.logging_params = logging_params
        self.metrics_queue = metrics_queue

        self.refresh_control_info()
        self.service = database.get_service_attributes(self.db_conn, service_slug)
        self.service['slug'] = service_slug

        self.supervisor = RunnerSupervisor(metrics_queue)
        self.known_tick = -1
        # Trigger launch of tasks in first step()
        self.last_launch = get_monotonic_time() - self.interval
        self.tasks_per_launch = None
        self.shutting_down = False

    def refresh_control_info(self):
        control_info = database.get_control_info(self.db_conn)
        self.contest_start = control_info['contest_start']
        self.tick_duration = datetime.timedelta(seconds=control_info['tick_duration'])
        self.flag_valid_ticks = control_info['valid_ticks']
        self.flag_prefix = control_info['flag_prefix']

    def step(self):
        """
        Handles a request from the supervisor, kills overdue tasks and launches new ones.
        Only processes one request at a time to make sure that launch_tasks() gets called regularly and
        long-running tasks get killed, at the cost of accumulating a backlog of messages.

        Returns:
            A boolean indicating whether a request was handled.
        """
        req = self.supervisor.get_request()
        if req is not None:
            resp = None
            send_resp = True

            try:
                if req['action'] == ACTION_FLAG:
                    resp = self.handle_flag_request(req['info'], req['param'])
                elif req['action'] == ACTION_FLAGID:
                    self.handle_flagid_request(req['info'], req['param'])
                elif req['action'] == ACTION_LOAD:
                    resp = self.handle_load_request(req['info'], req['param'])
                elif req['action'] == ACTION_STORE:
                    self.handle_store_request(req['info'], req['param'])
                elif req['action'] == ACTION_RESULT:
                    self.handle_result_request(req['info'], req['param'])
                else:
                    logging.error('Unknown action received from Checker Script for team %d (net number %d) '
                                  'in tick %d: %s', req['info']['_team_id'], req['info']['team'],
                                  req['info']['tick'], req['action'])
                    # We can't signal an error to the Checker Script (which might be waiting for a response),
                    # so our only option is to kill it
                    self.supervisor.terminate_runner(req['runner_id'])
                    metrics.inc(self.metrics_queue, 'killed_tasks')
                    send_resp = False
            except:    # noqa, pylint: disable=bare-except
                logging.exception('Checker Script communication error for team %d (net number %d) in tick '
                                  '%d:', req['info']['_team_id'], req['info']['team'], req['info']['tick'])
                self.supervisor.terminate_runner(req['runner_id'])
                metrics.inc(self.metrics_queue, 'killed_tasks')
            else:
                if send_resp:
                    req['send'].send(resp)

        if not self.shutting_down:
            # Launch new tasks and catch up missed intervals
            while get_monotonic_time() - self.last_launch >= self.interval:
                delay = get_monotonic_time() - self.last_launch - self.interval
                metrics.observe(self.metrics_queue, 'task_launch_delay_seconds', delay)
                metrics.set(self.metrics_queue, 'last_launch_timestamp', time.time())

                self.last_launch += self.interval
                self.launch_tasks()

        return req is not None

    def handle_flag_request(self, task_info, params):
        try:
            tick = int(params['tick'])
        except (KeyError, ValueError):
            return None

        # We need current value for self.contest_start which might have changed
        self.refresh_control_info()

        flag_id = database.get_flag_id(self.db_conn, self.service['id'], task_info['_team_id'], tick)

        expiration = self.contest_start + (self.flag_valid_ticks + tick) * self.tick_duration
        return flag_lib.generate(expiration, flag_id, task_info['team'], self.flag_secret,
                                 self.flag_prefix)

    def handle_flagid_request(self, task_info, param):
        database.set_flagid(self.db_conn, self.service['id'], task_info['team'], task_info['tick'], param)

    def handle_load_request(self, task_info, param):
        return database.load_state(self.db_conn, self.service['id'], task_info['team'], param)

    def handle_store_request(self, task_info, params):
        database.store_state(self.db_conn, self.service['id'], task_info['team'], params['key'],
                             params['data'])

    def handle_result_request(self, task_info, param):
        try:
            result = int(param)
        except ValueError:
            logging.error('Invalid result from Checker Script for team %d (net number %d) in tick %d: %s',
                          task_info['_team_id'], task_info['team'], task_info['tick'], param)
            return

        try:
            check_result = CheckResult(result)
        except ValueError:
            logging.error('Invalid result from Checker Script for team %d (net number %d) in tick %d: %d',
                          task_info['_team_id'], task_info['team'], task_info['tick'], result)
            return

        logging.info('Result from Checker Script for team %d (net number %d) in tick %d: %s',
                     task_info['_team_id'], task_info['team'], task_info['tick'], check_result)
        metrics.inc(self.metrics_queue, 'completed_tasks', labels={'result': check_result.name})
        database.commit_result(self.db_conn, self.service['id'], task_info['team'], task_info['tick'],
                               result)

    def launch_tasks(self):
        def timeout_runners():
            for task_info in self.supervisor.terminate_runners():
                logging.info('Forcefully terminated Checker Script for team %d (net number %d) in tick %d',
                             task_info['_team_id'], task_info['team'], task_info['tick'])
                metrics.inc(self.metrics_queue, 'timeout_tasks')
                database.commit_result(self.db_conn, self.service['id'], task_info['team'],
                                       task_info['tick'], STATUS_TIMEOUT)

        def change_tick(new_tick):
            timeout_runners()
            self.update_launch_params(new_tick)
            self.known_tick = new_tick

        current_tick, cancel_checks = database.get_current_tick(self.db_conn)
        if current_tick < 0:
            # Competition not running yet
            return
        if current_tick != self.known_tick:
            change_tick(current_tick)
        elif cancel_checks:
            # Competition over
            timeout_runners()
            return

        tasks = database.get_new_tasks(self.db_conn, self.service['id'], self.tasks_per_launch)

        # The current tick might have changed since calling `database.get_current_tick()`, so terminate the
        # old Runners; `database.get_new_tasks()` only returns tasks for one single tick
        if len(tasks) > 0 and tasks[0]['tick'] != current_tick:
            current_tick = tasks[0]['tick']
            change_tick(current_tick)

        for task in tasks:
            ip = self.ip_pattern % task['team_net_no']
            runner_args = [self.checker_script, ip, str(task['team_net_no']), str(task['tick'])]

            # Information in task_info should be somewhat human-readable, because it also ends up in Checker
            # Script logs
            task_info = {'service': self.service['slug'],
                         'team': task['team_net_no'],
                         '_team_id': task['team_id'],
                         'tick': task['tick']}
            logging.info('Starting Checker Script for team %d (net number %d) in tick %d', task['team_id'],
                         task['team_net_no'], task['tick'])
            self.supervisor.start_runner(runner_args, self.sudo_user, task_info, self.logging_params)

    def update_launch_params(self, tick):
        """
        Determines the number of Checker tasks to start per launch.
        Our goal here is to balance the load over a tick with some smearing (to make Checker fingerprinting
        more difficult), while also ensuring that all teams get checked in every tick.
        This implementation distributes the start of tasks evenly across the available time with some safety
        margin at the end. The duration of a check is determined from previous ticks after the first 5 ticks,
        before that the maximum is assumed.
        """

        if tick < 5:
            # We don't know any bounds on Checker Script Runtime at the beginning
            check_duration = self.tick_duration.total_seconds()
        else:
            check_duration = database.get_check_duration(self.db_conn, self.service['id'],
                                                         self.std_dev_count)
            if check_duration is None:
                # No complete flag placements so far
                check_duration = self.tick_duration.total_seconds()

        total_tasks = database.get_task_count(self.db_conn, self.service['id'])
        local_tasks = math.ceil(total_tasks / self.checker_count)

        margin_seconds = database.get_service_margin(self.db_conn, self.service['slug'])
        launch_timeframe = max(self.tick_duration.total_seconds() - check_duration - margin_seconds, 0)

        intervals_per_timeframe = math.floor(launch_timeframe / self.interval) + 1
        self.tasks_per_launch = math.ceil(local_tasks / intervals_per_timeframe)
        logging.info('Planning to start %d tasks per interval with a maximum duration of %d seconds (plus '
                     '%d seconds margin)', self.tasks_per_launch, check_duration, margin_seconds)
        metrics.set(self.metrics_queue, 'tasks_per_launch_count', self.tasks_per_launch)
        metrics.set(self.metrics_queue, 'max_task_duration_seconds', check_duration)

    def get_running_script_count(self):
        return len(self.supervisor.processes)


def get_monotonic_time():
    """
    Wrapper around time.monotonic() to enables mocking in test cases. Globally mocking time.monotonic()
    breaks library code (e.g. multiprocessing in RunnerSupervisor).
    """

    return time.monotonic()
