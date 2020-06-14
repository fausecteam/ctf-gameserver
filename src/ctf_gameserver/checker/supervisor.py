import json
import logging
import multiprocessing
import os
import queue
import select
import signal
import subprocess
import sys

from ctf_gameserver.lib.checkresult import CheckResult


ACTION_FLAG = 'FLAG'
ACTION_LOAD = 'LOAD'
ACTION_STORE = 'STORE'
ACTION_LOG = 'LOG'
ACTION_RESULT = 'RESULT'
ACTION_RUNNER_EXIT = 'RUNNER_EXIT'

ACTIONS = [
    ACTION_FLAG,
    ACTION_LOAD,
    ACTION_STORE,
    ACTION_LOG,
    ACTION_RESULT,
    ACTION_RUNNER_EXIT
]


class RunnerSupervisor:
    """
    Launches Checker Script Runners as individual processes and takes care of communicating with them.
    """

    def __init__(self):
        # Timeout if there are no requests when all Runners are done or blocking
        self.queue_timeout = 1
        self._reset()

    def _reset(self):
        self.work_queue = multiprocessing.Queue()
        self.processes = {}
        self.next_identifier = 0

    def start_runner(self, args, sudo_user, info, logging_params):
        logging.info('Starting Runner process, args: %s, info: %s', args, info)
        receive, send = multiprocessing.Pipe(False)
        proc = multiprocessing.Process(target=run_checker_script, args=(args, sudo_user, info,
                                                                        logging_params, self.next_identifier,
                                                                        self.work_queue, receive))
        self.processes[self.next_identifier] = (proc, send, info)

        proc.start()
        self.next_identifier += 1

    def terminate_runner(self, runner_id):
        logging.info('Terminating Runner process, info: %s', self.processes[runner_id][2])
        self.processes[runner_id][0].terminate()
        # Afterwards, get_request() will join the child and remove it from `self.processes`

    def terminate_runners(self):
        if len(self.processes) > 0:
            logging.warning('Terminating all %d Runner processes', len(self.processes))
            for runner_id in self.processes:
                self.terminate_runner(runner_id)

        # Prevent memory leaks
        self._reset()

    def get_request(self):
        # Use a loop to not leak our implementation detail for ACTION_RUNNER_EXIT: Only return None when the
        # queue is really empty (barring non-critical race conditions)
        while True:
            try:
                request = self.work_queue.get(True, self.queue_timeout)
            except queue.Empty:
                return None
            runner_id = request[0]
            action = request[1]

            # Join all terminated child processes
            if action == ACTION_RUNNER_EXIT:
                proc = self.processes[runner_id][0]
                proc.join()
                del self.processes[runner_id]
                if self.work_queue.empty():
                    return None
            else:
                break

        return {
            'action': action,
            'param': request[2],
            'runner_id': runner_id,
            'send': self.processes[runner_id][1],
            'info': self.processes[runner_id][2]
        }


def run_checker_script(args, sudo_user, info, logging_params, runner_id, queue_to_master, pipe_from_master):
    """
    Checker Script Runner, which is supposed to already be executed in an individual process. The actual
    Checker Script is then launched as another child process (one per Runner).
    We're also taking care of saving logs from the Checker Script here, since passing them to the Master
    process would put a lot of load on it.
    """

    runner_logger = logging.getLogger('Checker Runner: {}'.format(args))

    class InfoFilter(logging.Filter):
        """
        Log Filter which adds all metadata from an "info" dict as attributes to Log Records.
        """
        def __init__(self, info):
            super().__init__()
            self.info = info

        def filter(self, record):
            for key, value in self.info.items():
                if hasattr(record, key):
                    runner_logger.warning('Discarding log metadata "%s" due to a naming conflict', key)
                else:
                    setattr(record, key, value)
            return True

    script_logger = logging.getLogger('Checker Script')
    script_logger.setLevel(logging.INFO)
    script_logger.propagate = False
    if info is not None:
        script_logger.addFilter(InfoFilter(info))

    if 'journald' in logging_params:
        from systemd.journal import JournalHandler    # pylint: disable=import-outside-toplevel,import-error
        syslog_identifier = 'checker_{}-team{:03d}-tick{:03d}'.format(info['service'], info['team'],
                                                                      info['tick'])
        journal_handler = JournalHandler(SYSLOG_IDENTIFIER=syslog_identifier)
        script_logger.addHandler(journal_handler)
    if 'gelf' in logging_params:
        import graypy    # pylint: disable=import-outside-toplevel,import-error
        gelf_handler = graypy.GELFHandler(logging_params['gelf']['host'], logging_params['gelf']['port'])
        script_logger.addHandler(gelf_handler)

    stdout_read, stdout_write = os.pipe()
    stderr_read, stderr_write = os.pipe()
    ctrlin_read, ctrlin_write = os.pipe()
    ctrlout_read, ctrlout_write = os.pipe()

    # File descriptor numbers after dup_ctrl_fds()
    CTRLIN_FD = 3    # pylint: disable=invalid-name
    CTRLOUT_FD = 4    # pylint: disable=invalid-name

    def dup_ctrl_fds():
        """
        preexec_fn for subprocess.Popen() which forces specific numbers for file descriptors within the
        child. We need this because otherwise the child won't know the numbers of additional FDs.
        """
        os.dup2(ctrlin_read, CTRLIN_FD)
        os.close(ctrlin_read)
        os.dup2(ctrlout_write, CTRLOUT_FD)
        os.close(ctrlout_write)

    if sudo_user is not None:
        args = ['sudo', '--user='+sudo_user, '--preserve-env=PATH,CTF_CHECKERSCRIPT,CHECKERSCRIPT_PIDFILE',
                '--close-from=5', '--'] + args

    env = {**os.environ, 'CTF_CHECKERSCRIPT': '1'}
    # Python doesn't specify if preexec_fn gets executed before or after closing file descriptors, thus we
    # specify both variants as pass_fds
    try:
        proc = subprocess.Popen(args, env=env, shell=False,    # pylint: disable=subprocess-popen-preexec-fn
                                stdout=stdout_write, stderr=stderr_write,
                                pass_fds=(CTRLIN_FD, CTRLOUT_FD, ctrlin_read, ctrlout_write),
                                preexec_fn=dup_ctrl_fds, start_new_session=True)
    except OSError:
        runner_logger.exception('Executing Checker Script failed:')
        # Tell the Supervisor that we are safe to be joined
        queue_to_master.put((runner_id, ACTION_RUNNER_EXIT, None))
        return
    # Close the child's ends of the pipes on the parent's side
    os.close(stdout_write)
    os.close(stderr_write)
    os.close(ctrlin_read)
    os.close(ctrlout_write)

    # Kill all children when this process gets terminated (requires `start_new_session=True` above)
    def sigterm_handler(_, __):
        runner_logger.warning('Terminating Checker Script from Supervisor')
        # Yeah kids, this is how Unix works
        pgid = -1 * proc.pid
        kill_args = ['kill', '-KILL', str(pgid)]
        if sudo_user is not None:
            kill_args = ['sudo', '--user='+sudo_user, '--'] + kill_args
        subprocess.check_call(kill_args)
        sys.exit(1)
    signal.signal(signal.SIGTERM, sigterm_handler)

    poll = select.poll()
    poll.register(stdout_read, select.POLLIN | select.POLLERR | select.POLLHUP)
    poll.register(stderr_read, select.POLLIN | select.POLLERR | select.POLLHUP)
    poll.register(ctrlout_read, select.POLLIN | select.POLLERR | select.POLLHUP)

    # Loop until the child has terminated
    while proc.poll() is None:
        events = poll.poll()

        for event in events:
            if not (event[1] & select.POLLIN):    # pylint: disable=superfluous-parens
                # We only care if we can read, POLLERR and POLLHUP will terminate the child anyway
                continue

            fd = event[0]
            try:
                data = os.read(fd, 4096)
            except OSError:
                runner_logger.exception('Read from child pipe failed:')
                continue
            if len(data) == 0:
                # EOF (on this file descriptor)
                continue

            # Save everything the Checker Scripts writes to stdout or stderr as log message
            if fd in (stdout_read, stderr_read):
                script_output = data.decode('ascii', errors='backslashreplace').rstrip('\n')
                script_logger.warning('[SCRIPT OUTPUT] %s', script_output)
            # Communication with the Checker Script via single-line JSON objects
            else:
                buf = b''
                while True:
                    buf += data
                    lines = buf.split(b'\n')
                    for line in lines[:-1]:
                        try:
                            message = json.loads(line)
                        except json.JSONDecodeError:
                            runner_logger.error('Could not decode message from Script as JSON: %s', line)
                        else:
                            handle_script_message(message, ctrlin_write, runner_id, queue_to_master,
                                                  pipe_from_master, runner_logger, script_logger)

                    if len(lines[-1]) == 0:
                        # We have not read a partial line
                        break

                    buf = lines[-1]
                    try:
                        data = os.read(fd, 4096)
                    except OSError:
                        runner_logger.exception('Read from child pipe failed:')
                        break

    os.close(stdout_read)
    os.close(stderr_read)
    os.close(ctrlin_write)
    os.close(ctrlout_read)

    runner_logger.info('Checker Script exited with code %d', proc.returncode)
    # Tell the Supervisor that our child has exited and we are safe to be joined without blocking
    queue_to_master.put((runner_id, ACTION_RUNNER_EXIT, None))


def handle_script_message(message, ctrlin_fd, runner_id, queue_to_master, pipe_from_master, runner_logger,
                          script_logger):
    """
    Processes a single message from communication with a Checker Script. Communication is always initiated
    by the Checker Script, we (as the Runner) only respond.
    """

    try:
        action = message['action']
        param = message['param']
    except KeyError:
        runner_logger.error('Message must have "action" and "param" keys: %s', message)
        return

    if action not in ACTIONS:
        runner_logger.error('Message has invalid "action" key: %s', message)
        return
    if action == ACTION_RUNNER_EXIT:
        runner_logger.error('RUNNER_EXIT messages must not be generated by the Script: %s', message)
        return

    if action == ACTION_LOG:
        record = make_script_log_record(param)
        if record is None:
            runner_logger.error('Malformed log message from the Script: %s', param)
        else:
            script_logger.handle(record)
        return

    if action == ACTION_RESULT:
        try:
            result = CheckResult(int(param))
        except ValueError:
            # Ignore malformed message from the Checker Script, will be logged by the Master
            pass
        else:
            script_logger.info('CHECKER SCRIPT RESULT: %s', result.name, extra={'result': result.value})

    queue_to_master.put((runner_id, action, param))
    response = pipe_from_master.recv()

    try:
        # Make sure that our JSON consists of just a single line
        response_json = json.dumps({'response': response}).replace('\n', '') + '\n'
        os.write(ctrlin_fd, response_json.encode())
    except OSError:
        runner_logger.exception('Write to child pipe failed:')


def make_script_log_record(json_record):

    # Use actual message as "args" to prevent format string injections
    msg = '%s'
    try:
        args = (str(json_record['message']),)
    except KeyError:
        return None

    try:
        level = int(json_record['levelno'])
    except (KeyError, ValueError):
        level = logging.INFO
    pathname = str(json_record.get('pathname', '<unknown>'))
    try:
        lineno = int(json_record['lineno'])
    except (KeyError, ValueError):
        lineno = 0
    func = str(json_record.get('funcName', '<unknown>'))

    return logging.LogRecord('Checker Script', level, pathname, lineno, msg, args, None, func)
