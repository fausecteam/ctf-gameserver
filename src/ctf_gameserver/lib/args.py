import configargparse
import shlex


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
