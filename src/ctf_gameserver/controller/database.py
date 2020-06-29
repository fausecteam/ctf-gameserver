import logging

import psycopg2

from ctf_gameserver.lib.database import transaction_cursor
from ctf_gameserver.lib.date_time import ensure_utc_aware
from ctf_gameserver.lib.exceptions import DBDataError


def connect_to_db(db_host, db_name, db_user, db_password):
    """
    Establishes a Psycopg2 connection to the database.

    Returns:
        The new connection, or None if it could not be establised.
    """

    try:
        db_conn = psycopg2.connect(host=db_host, database=db_name, user=db_user, password=db_password)
    except psycopg2.OperationalError as e:
        logging.error('Could not establish database connection: %s', e)
        return None
    logging.info('Established database connection')

    return db_conn


def get_control_info(db_conn, prohibit_changes=False):
    """
    Returns a dictionary containing relevant information about the competion, as stored in the database.
    """

    with transaction_cursor(db_conn, prohibit_changes) as cursor:
        cursor.execute('SELECT start, "end", tick_duration, current_tick FROM scoring_gamecontrol')
        result = cursor.fetchone()

    if result is None:
        raise DBDataError('Game control information has not been configured')
    start, end, duration, tick = result

    return {
        'start': ensure_utc_aware(start),
        'end': ensure_utc_aware(end),
        'tick_duration': duration,
        'current_tick': tick
    }


def increase_tick(db_conn, prohibit_changes=False):

    with transaction_cursor(db_conn, prohibit_changes) as cursor:
        cursor.execute('UPDATE scoring_gamecontrol SET current_tick = current_tick + 1')
        # Create flags for every service and team in the new tick
        cursor.execute('INSERT INTO scoring_flag (service_id, protecting_team_id, tick)'
                       '    SELECT service.id, team.user_id, control.current_tick'
                       '    FROM scoring_service service, auth_user, registration_team team,'
                       '         scoring_gamecontrol control'
                       '    WHERE auth_user.id = team.user_id AND auth_user.is_active')


def update_scoring(db_conn):

    with transaction_cursor(db_conn) as cursor:
        cursor.execute('UPDATE scoring_flag as outerflag'
                       '    SET bonus = 1 / ('
                       '        SELECT greatest(1, count(*))'
                       '        FROM scoring_flag'
                       '        LEFT OUTER JOIN scoring_capture ON scoring_capture.flag_id = scoring_flag.id'
                       '        WHERE scoring_capture.flag_id = outerflag.id)'
                       '    FROM scoring_gamecontrol'
                       '    WHERE outerflag.tick + scoring_gamecontrol.valid_ticks < '
                       '        scoring_gamecontrol.current_tick AND outerflag.bonus IS NULL')
        cursor.execute('REFRESH MATERIALIZED VIEW "scoring_scoreboard"')
