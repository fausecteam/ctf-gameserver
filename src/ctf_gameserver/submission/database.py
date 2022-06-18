import sqlite3

# See https://github.com/PyCQA/pylint/issues/2948 for Pylint behavior
from psycopg2.errors import UniqueViolation    # pylint: disable=no-name-in-module

from ctf_gameserver.lib.database import transaction_cursor
from ctf_gameserver.lib.date_time import ensure_utc_aware
from ctf_gameserver.lib.exceptions import DBDataError


def get_static_info(db_conn):
    """
    Returns the competition's name and the flag prefix, as configured in the database.
    """

    with transaction_cursor(db_conn) as cursor:
        cursor.execute('SELECT competition_name, flag_prefix FROM scoring_gamecontrol')
        result = cursor.fetchone()

    if result is None:
        raise DBDataError('Game control information has not been configured')

    return result


def get_dynamic_info(db_conn):
    """
    Returns the competition's start and end time, as stored in the database.
    """

    with transaction_cursor(db_conn) as cursor:
        cursor.execute('SELECT start, "end" FROM scoring_gamecontrol')
        result = cursor.fetchone()

    if result is None:
        raise DBDataError('Game control information has not been configured')

    return (ensure_utc_aware(result[0]), ensure_utc_aware(result[1]))


def team_is_nop(db_conn, team_net_no):
    """
    Returns whether the team with the given net number is marked as NOP team.
    """

    with transaction_cursor(db_conn) as cursor:
        cursor.execute('SELECT nop_team FROM registration_team WHERE net_number = %s', (team_net_no,))
        result = cursor.fetchone()

    if result is None:
        return False

    return result[0]


def add_capture(db_conn, flag_id, capturing_team_net_no, prohibit_changes=False, fake_team_id=None,
                fake_tick=None):
    """
    Stores a capture of the given flag by the given team in the database.
    """

    with transaction_cursor(db_conn, prohibit_changes) as cursor:
        cursor.execute('SELECT user_id FROM registration_team WHERE net_number = %s',
                       (capturing_team_net_no,))
        result = cursor.fetchone()
        if fake_team_id is not None:
            result = (fake_team_id,)
        if result is None:
            raise TeamNotExisting()
        capturing_team_id = result[0]

        cursor.execute('SELECT current_tick FROM scoring_gamecontrol')
        result = cursor.fetchone()
        if fake_tick is not None:
            result = (fake_tick,)
        tick = result[0]

        try:
            cursor.execute('INSERT INTO scoring_capture (flag_id, capturing_team_id, timestamp, tick)'
                           '    VALUES (%s, %s, NOW(), %s)', (flag_id, capturing_team_id, tick))
        except (UniqueViolation, sqlite3.IntegrityError):
            raise DuplicateCapture() from None


class TeamNotExisting(DBDataError):
    """
    Indicates that a Team for the given parameters could not be found in the database.
    """


class DuplicateCapture(DBDataError):
    """
    Indicates that a Flag has already been captured by a Team before.
    """
