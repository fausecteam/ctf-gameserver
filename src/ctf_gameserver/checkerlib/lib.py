#!/usr/bin/env python3

import base64
import datetime
import errno
import http.client
import json
import logging
import os
import pickle    # nosec
import socket
import ssl
import sys
import threading
from typing import Any, Type

import ctf_gameserver.lib.flag
from ctf_gameserver.lib.checkresult import CheckResult


_TIMEOUT_SECONDS = 10.0    # Default timeout for socket operations
_LOCAL_STATE_PATH_TMPL = '_{team:d}_state.json'
_LOCAL_STATE_PATH = None

_ctrl_in = None    # pylint: disable=invalid-name
_ctrl_out = None    # pylint: disable=invalid-name
_ctrl_out_lock = None    # pylint: disable=invalid-name


def _setup():

    global _ctrl_in, _ctrl_out, _ctrl_out_lock    # pylint: disable=invalid-name
    if 'CTF_CHECKERSCRIPT' in os.environ:
        # Launched by Checker Runner, we cannot just try to open the descriptors (and fallback if they don't
        # exist) because execution environments like pytest might use them as well
        _ctrl_in = os.fdopen(3, 'r')
        _ctrl_out = os.fdopen(4, 'w')
    else:
        # Local execution without a Checker Runner
        logging.basicConfig()
        logging.getLogger().setLevel(logging.INFO)
        return

    _ctrl_out_lock = threading.RLock()

    class JsonHandler(logging.StreamHandler):
        def __init__(self):
            super().__init__(_ctrl_out)

        def emit(self, record):
            _ctrl_out_lock.acquire()
            super().emit(record)
            _ctrl_out_lock.release()

        def format(self, record):
            param = {
                'message': super().format(record),
                'levelno': record.levelno,
                'pathname': record.pathname,
                'lineno': record.lineno,
                'funcName': record.funcName
            }
            json_message = {'action': 'LOG', 'param': param}
            # Make sure that our JSON consists of just a single line
            return json.dumps(json_message).replace('\n', '')

    json_handler = JsonHandler()
    logging.getLogger().addHandler(json_handler)
    logging.getLogger().setLevel(logging.INFO)

    socket.setdefaulttimeout(_TIMEOUT_SECONDS)
    try:
        import requests    # pylint: disable=import-outside-toplevel

        # Ugly monkey patch to set defaults for the timeouts in requests, because requests (resp. urllib3)
        # always overwrites the default socket timeout
        class TimeoutSoup(requests.adapters.TimeoutSauce):
            def __init__(self, total=None, connect=None, read=None):
                if total is None:
                    total = _TIMEOUT_SECONDS
                if connect is None:
                    connect = _TIMEOUT_SECONDS
                if read is None:
                    read = _TIMEOUT_SECONDS
                super().__init__(total, connect, read)
        requests.adapters.TimeoutSauce = TimeoutSoup
    except ImportError:
        pass


_setup()


class BaseChecker:
    """
    Base class for individual Checker implementations. Checker Scripts must implement all methods.

    Attributes:
        ip: Vulnbox IP address of the team to be checked
        team: Net number of the team to be checked
    """

    def __init__(self, ip: str, team: int) -> None:
        self.ip = ip
        self.team = team

    def place_flag(self, tick: int) -> CheckResult:
        raise NotImplementedError('place_flag() must be implemented by the subclass')

    def check_service(self) -> CheckResult:
        raise NotImplementedError('check_service() must be implemented by the subclass')

    def check_flag(self, tick: int) -> CheckResult:
        raise NotImplementedError('check_flag() must be implemented by the subclass')


def get_flag(tick: int) -> str:
    """
    May be called by Checker Scripts to get the flag for a given tick, for the team and service of the
    current run. The returned flag can be used for both placement and checks.
    """

    if not isinstance(tick, int):
        raise TypeError('tick must be of type int')

    # Return dummy flag when launched locally
    if _launched_without_runner():
        try:
            team = get_flag._team    # pylint: disable=protected-access
        except AttributeError:
            raise Exception('get_flag() must be called through run_check()') from None
        expiration = datetime.datetime(1970, 1, 1, 0, 0, tzinfo=datetime.timezone.utc)
        expiration += datetime.timedelta(minutes=tick)
        return ctf_gameserver.lib.flag.generate(expiration, 42, team, b'TOPSECRET')

    _send_ctrl_message({'action': 'FLAG', 'param': {'tick': tick}})
    result = _recv_ctrl_message()
    return result['response']


def set_flagid(data: str) -> None:
    """
    Stores the Flag ID for the current team and tick.
    """

    if not isinstance(data, str):
        raise TypeError('data must be of type str')
    if len(data) > 200:
        raise AttributeError('data must not be longer than 200 bytes')

    if not _launched_without_runner():
        _send_ctrl_message({'action': 'FLAGID', 'param': data})
        # Wait for acknowledgement
        _recv_ctrl_message()
    else:
        print('Storing Flag ID: {}'.format(data))


def store_state(key: str, data: Any) -> None:
    """
    Allows a Checker Script to store arbitrary Python data persistently across runs. Data is stored per
    service and team with the given key as an additional identifier.
    """

    if not isinstance(key, str):
        raise TypeError('key must be of type str')

    serialized_data = base64.b64encode(pickle.dumps(data)).decode('ascii')

    if not _launched_without_runner():
        message = {'key': key, 'data': serialized_data}
        _send_ctrl_message({'action': 'STORE', 'param': message})
        # Wait for acknowledgement
        _recv_ctrl_message()
    else:
        try:
            with open(_LOCAL_STATE_PATH, 'r', encoding='utf-8') as f:
                state = json.load(f)
        except FileNotFoundError:
            state = {}
        state[key] = serialized_data
        with open(_LOCAL_STATE_PATH, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=4)


def load_state(key: str) -> Any:
    """
    Allows to retrieve data stored through store_state(). If no data exists for the given key (and the
    current service and team), None is returned.
    """

    if not isinstance(key, str):
        raise TypeError('key must be of type str')

    if not _launched_without_runner():
        _send_ctrl_message({'action': 'LOAD', 'param': key})
        result = _recv_ctrl_message()
        data = result['response']
        if data is None:
            return None
    else:
        try:
            with open(_LOCAL_STATE_PATH, 'r', encoding='utf-8') as f:
                state = json.load(f)
        except FileNotFoundError:
            return None
        try:
            data = state[key]
        except KeyError:
            return None

    return pickle.loads(base64.b64decode(data))    # nosec


def run_check(checker_cls: Type[BaseChecker]) -> None:
    """
    Launch execution of the specified Checker implementation. Must be called by all Checker Scripts.
    """

    if len(sys.argv) != 4:
        raise Exception('Invalid arguments, usage: {} <ip> <team-net-no> <tick>'.format(sys.argv[0]))

    ip = sys.argv[1]
    team = int(sys.argv[2])
    tick = int(sys.argv[3])

    global _LOCAL_STATE_PATH
    _LOCAL_STATE_PATH = _LOCAL_STATE_PATH_TMPL.format(team=team)

    if _launched_without_runner():
        # Hack because get_flag() only needs to know the team when launched locally
        get_flag._team = team    # pylint: disable=protected-access

    checker = checker_cls(ip, team)
    result = _run_check_steps(checker, tick)

    if not _launched_without_runner():
        _send_ctrl_message({'action': 'RESULT', 'param': result.value})
        # Wait for acknowledgement
        _recv_ctrl_message()
    else:
        print('Check result: {}'.format(result))


def _run_check_steps(checker, tick):

    tick_lookback = 5

    try:
        logging.info('Placing flag')
        result = checker.place_flag(tick)
        logging.info('Flag placement result: %s', result)
        if result != CheckResult.OK:
            return result

        logging.info('Checking service')
        result = checker.check_service()
        logging.info('Service check result: %s', result)
        if result != CheckResult.OK:
            return result

        current_tick = tick
        oldest_tick = max(tick-tick_lookback, 0)
        recovering = False
        while current_tick >= oldest_tick:
            logging.info('Checking flag of tick %d', current_tick)
            result = checker.check_flag(current_tick)
            logging.info('Flag check result of tick %d: %s', current_tick, result)
            if result != CheckResult.OK:
                if current_tick != tick and result == CheckResult.FLAG_NOT_FOUND:
                    recovering = True
                else:
                    return result
            current_tick -= 1

        if recovering:
            return CheckResult.RECOVERING
        else:
            return CheckResult.OK
    except Exception as e:    # pylint: disable=broad-except
        if _is_conn_error(e):
            logging.warning('Connection error during check', exc_info=e)
            return CheckResult.DOWN
        else:
            # Just let the Checker Script die, logging will be handled by the Runner
            raise e


def _launched_without_runner():
    """
    Returns True if the Checker Script has been launched locally (during development) and False if it has
    been launched by the Checker Script Runner (during an actual competition).
    """
    return _ctrl_in is None


def _recv_ctrl_message():

    message_json = _ctrl_in.readline()
    return json.loads(message_json)


def _send_ctrl_message(message):

    # Make sure that our JSON consists of just a single line
    message_json = json.dumps(message).replace('\n', '') + '\n'

    _ctrl_out_lock.acquire()
    _ctrl_out.write(message_json)
    _ctrl_out.flush()
    _ctrl_out_lock.release()


def _is_conn_error(exception):
    """
    Checks if the given exception resembles an error in the network connection, e.g. a timeout or connection
    abort.
    """

    conn_exceptions = (
        BrokenPipeError,    # Raised on SIGPIPE
        ConnectionAbortedError,
        ConnectionResetError,
        ConnectionRefusedError,
        EOFError,    # Raised by telnetlib on timeout
        http.client.BadStatusLine,
        http.client.ImproperConnectionState,
        http.client.LineTooLong,
        http.client.UnknownTransferEncoding,
        socket.timeout,
        ssl.SSLEOFError,
        ssl.SSLWantReadError,
        ssl.SSLWantWriteError,
        ssl.SSLZeroReturnError
    )
    try:
        import urllib3    # pylint: disable=import-outside-toplevel
        conn_exceptions += (
            urllib3.exceptions.ConnectionError,
            urllib3.exceptions.DecodeError,
            urllib3.exceptions.IncompleteRead,
            urllib3.exceptions.ProtocolError,
            urllib3.exceptions.SSLError,
            urllib3.exceptions.TimeoutError
        )
    except ImportError:
        pass
    try:
        import requests    # pylint: disable=import-outside-toplevel
        conn_exceptions += (
            requests.Timeout,
            requests.ConnectionError,
            requests.packages.urllib3.exceptions.ConnectionError,
            requests.packages.urllib3.exceptions.DecodeError,
            requests.packages.urllib3.exceptions.IncompleteRead,
            requests.packages.urllib3.exceptions.ProtocolError,
            requests.packages.urllib3.exceptions.SSLError,
            requests.packages.urllib3.exceptions.TimeoutError
        )
    except ImportError:
        pass
    try:
        import nclib    # pylint: disable=import-outside-toplevel
        conn_exceptions += (nclib.NetcatError,)
    except ImportError:
        pass

    if isinstance(exception, conn_exceptions):
        return True

    # (At least) urllib and urllib3 wrap other exceptions in a "reason" attribute
    if hasattr(exception, 'reason') and isinstance(exception.reason, Exception):
        return _is_conn_error(exception.reason)

    if isinstance(exception, OSError):
        return exception.errno in (
            errno.EACCES,
            errno.ECONNABORTED,
            errno.ECONNREFUSED,
            errno.ECONNRESET,
            errno.EHOSTDOWN,
            errno.EHOSTUNREACH,
            errno.ENETDOWN,
            errno.ENETRESET,
            errno.ENETUNREACH,
            errno.EPIPE,
            errno.ETIMEDOUT
        )

    return False
