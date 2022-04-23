import socket
import urllib.parse

import configargparse


def get_arg_parser_with_db(description):
    """
    Returns an ArgumentParser pre-initalized with common arguments for configuring logging and the main
    database connection. It also supports reading arguments from environment variables.
    """

    parser = configargparse.ArgumentParser(description=description, auto_env_var_prefix='ctf_')

    parser.add_argument('--loglevel', default='WARNING', type=str,
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], help='Log level')

    db_group = parser.add_argument_group('database', 'Gameserver database')
    db_group.add_argument('--dbhost', type=str, help='Hostname of the database. If unspecified, the '
                          'default Unix socket will be used.')
    db_group.add_argument('--dbname', type=str, required=True, help='Name of the used database')
    db_group.add_argument('--dbuser', type=str, required=True, help='User name for database access')
    db_group.add_argument('--dbpassword', type=str, help='Password for database access if needed')

    return parser


def parse_host_port(text):

    """
    Parses a host and port specification from a string in the format `<host>:<port>`.

    Returns:
        The parsing result as a tuple of (host, port, family). `family` is a constant from Python's socket
        interface representing an address family, e.g. `socket.AF_INET`.
    """

    # Use pseudo URL for splitting, see https://stackoverflow.com/a/53172593
    url_parts = urllib.parse.urlsplit('//' + text)
    if url_parts.hostname is None or url_parts.port is None:
        raise ValueError('Invalid host or port')

    try:
        addrinfo = socket.getaddrinfo(url_parts.hostname, url_parts.port)
    except socket.gaierror as e:
        raise ValueError('Could not determine address family') from e

    return (url_parts.hostname, url_parts.port, addrinfo[0][0])
