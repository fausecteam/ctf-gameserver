import argparse
import shlex


def get_arg_parser_with_db(description):
    """
    Returns an ArgumentParser pre-initalized with common arguments for configuring logging and the main
    database connection. It also has improved behavior when reading arguments from config files.
    """

    parser = argparse.ArgumentParser(description=description, fromfile_prefix_chars='@')
    parser.convert_arg_line_to_args = convert_arg_line_to_args

    parser.add_argument('--loglevel', default='WARNING', type=str,
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], help='Log level')

    db_group = parser.add_argument_group('database', 'Gameserver database')
    db_group.add_argument('--dbhost', type=str, help='Hostname of the database. If unspecified, the '
                          'default Unix socket will be used.')
    db_group.add_argument('--dbname', type=str, required=True, help='Name of the used database')
    db_group.add_argument('--dbuser', type=str, required=True, help='User name for database access')
    db_group.add_argument('--dbpassword', type=str, help='Password for database access if needed')

    return parser


def convert_arg_line_to_args(arg_line):
    """
    Argparse helper for splitting input from config.
    Allows comment lines in configfiles and allows both argument and value on the same line.
    """

    return shlex.split(arg_line, comments=True)
