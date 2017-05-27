""" Useful functions for checkers. """

import socket
import errno
import ssl
import urllib3
import requests

def is_timeout(ex):
    """ Is this exception due to a timeout/connection error? """

    exception_types = (
        socket.timeout,
        requests.exceptions.Timeout,
        requests.exceptions.ConnectTimeout,
        requests.packages.urllib3.exceptions.ConnectionError,
        urllib3.exceptions.ConnectionError,
        urllib3.exceptions.ReadTimeoutError,
        EOFError, # telnetlib
        ssl.SSLEOFError,
        ssl.SSLZeroReturnError,
        ssl.SSLWantReadError,
        ssl.SSLWantWriteError,
        )
    # these only exist in recent urllib3 versions:
    if hasattr(requests.packages.urllib3.exceptions, 'NewConnectionError'):
        exception_types += (requests.packages.urllib3.exceptions.NewConnectionError,)
    if hasattr(urllib3.exceptions, 'NewConnectionError'):
        exception_types += (urllib3.exceptions.NewConnectionError,)

    if isinstance(ex, exception_types):
        return True

    if isinstance(ex, requests.exceptions.ConnectionError):
        return len(ex.args) == 1 and is_timeout(ex.args[0])
    if isinstance(ex, (urllib3.exceptions.MaxRetryError,
                       requests.packages.urllib3.exceptions.MaxRetryError)):
        return is_timeout(ex.reason)
    if isinstance(ex, (urllib3.exceptions.ProtocolError,
                       requests.packages.urllib3.exceptions.ProtocolError)):
        return len(ex.args) == 2 and is_timeout(ex.args[1])
    if isinstance(ex, OSError):
        return ex.errno in (errno.ETIMEDOUT, errno.ECONNREFUSED, errno.EHOSTDOWN,
                            errno.EHOSTUNREACH, errno.ENETUNREACH, errno.ENETDOWN,
                            errno.ENETRESET, errno.ECONNRESET, errno.ECONNABORTED,
                            errno.EPIPE)
    return False
