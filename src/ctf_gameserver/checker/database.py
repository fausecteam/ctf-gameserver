from ctf_gameserver.lib.database import transaction_cursor
from ctf_gameserver.lib.exceptions import DBDataError


def get_control_info(db_conn, prohibit_changes=False):
    """
    Returns a dictionary containing relevant information about the competion, as stored in the game database.
    """

    with transaction_cursor(db_conn, prohibit_changes) as cursor:
        cursor.execute('SELECT start, valid_ticks, tick_duration FROM scoring_gamecontrol')
        result = cursor.fetchone()

    if result is None:
        raise DBDataError('Game control information has not been configured')

    return {
        'contest_start': result[0],
        'valid_ticks': result[1],
        'tick_duration': result[2]
    }


def get_service_attributes(db_conn, service_slug, prohibit_changes=False):
    """
    Returns ID and name of a service for a given slug.
    """

    with transaction_cursor(db_conn, prohibit_changes) as cursor:
        cursor.execute('SELECT id, name FROM scoring_service WHERE slug = %s', (service_slug,))
        result = cursor.fetchone()

    if result is None:
        raise DBDataError('Service has not been configured')

    return {
        'id': result[0],
        'name': result[1]
    }


def get_current_tick(db_conn, prohibit_changes=False):
    """
    Reads the current tick from the game database.
    """

    with transaction_cursor(db_conn, prohibit_changes) as cursor:
        cursor.execute('SELECT current_tick FROM scoring_gamecontrol')
        result = cursor.fetchone()

    if result is None:
        raise DBDataError('Game control information has not been configured')

    return result[0]


def get_task_count(db_conn, service_id, prohibit_changes=False):
    """
    Returns the total number of tasks for the given service in the current tick.
    With our current Controller implementation, this should always be equal to the number of teams.
    """

    with transaction_cursor(db_conn, prohibit_changes) as cursor:
        cursor.execute('SELECT COUNT(*)'
                       '    FROM scoring_flag flag, scoring_gamecontrol control'
                       '    WHERE flag.tick = control.current_tick'
                       '        AND flag.service_id = %s', (service_id,))
        result = cursor.fetchone()

    return result[0]


def get_new_tasks(db_conn, service_id, task_count, prohibit_changes=False):
    """
    Retrieves the given number of random open check tasks and marks them as in progress.
    """

    with transaction_cursor(db_conn, prohibit_changes) as cursor:
        cursor.execute('SELECT flag.id, flag.protecting_team_id, flag.tick'
                       '    FROM scoring_flag flag, scoring_gamecontrol control'
                       '    WHERE flag.placement_start is NULL'
                       '        AND flag.tick = control.current_tick'
                       '        AND flag.service_id = %s'
                       '    ORDER BY RANDOM()'
                       '    LIMIT %s'
                       '    FOR UPDATE OF flag', (service_id, task_count))
        tasks = cursor.fetchall()

        # Mark placement as in progress
        cursor.executemany('UPDATE scoring_flag'
                           '    SET placement_start = NOW()'
                           '    WHERE id = %s', [(task[0],) for task in tasks])

    return [{
        'team_id': task[1],
        'tick': task[2]
    } for task in tasks]


def commit_result(db_conn, service_id, team_id, tick, result, prohibit_changes=False):
    """
    Saves the result from a Checker run to game database.
    """

    with transaction_cursor(db_conn, prohibit_changes) as cursor:
        cursor.execute('INSERT INTO scoring_statuscheck'
                       '    (service_id, team_id, tick, status, timestamp)'
                       '    VALUES (%s, %s, %s, %s, NOW())', (service_id, team_id, tick, result))
        # (In case of `prohibit_changes`,) PostgreSQL checks the database grants even if nothing is matched
        # by `WHERE`
        cursor.execute('UPDATE scoring_flag'
                       '    SET placement_end = NOW()'
                       '    WHERE service_id = %s AND protecting_team_id = %s AND tick = %s', (service_id,
                                                                                               team_id,
                                                                                               tick))


def load_state(db_conn, service_id, team_id, identifier, prohibit_changes=False):
    """
    Loads Checker data from state database.
    """

    with transaction_cursor(db_conn, prohibit_changes) as cursor:
        cursor.execute('SELECT data FROM checkerstate'
                       '    WHERE service_id = %s'
                       '        AND team_id = %s'
                       '        AND identifier = %s', (service_id, team_id, identifier))
        data = cursor.fetchone()

    if data is None:
        return None
    return data[0]


def store_state(db_conn, service_id, team_id, identifier, data, prohibit_changes=False):
    """
    Stores Checker data in state database.
    """

    with transaction_cursor(db_conn, prohibit_changes) as cursor:
        # (In case of `prohibit_changes`,) PostgreSQL checks the database grants even if no CONFLICT occurs
        cursor.execute('INSERT INTO checkerstate (service_id, team_id, identifier, data)'
                       '    VALUES (%s, %s, %s, %s)'
                       '    ON CONFLICT (service_id, team_id, identifier)'
                       '        DO UPDATE SET data = EXCLUDED.data', (service_id, team_id, identifier, data))
