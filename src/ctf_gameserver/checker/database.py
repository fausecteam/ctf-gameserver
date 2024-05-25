import logging

from ctf_gameserver.lib.checkresult import STATUS_TIMEOUT
from ctf_gameserver.lib.database import transaction_cursor
from ctf_gameserver.lib.exceptions import DBDataError


def get_control_info(db_conn, prohibit_changes=False):
    """
    Returns a dictionary containing relevant information about the competion, as stored in the game database.
    """

    with transaction_cursor(db_conn, prohibit_changes) as cursor:
        cursor.execute('SELECT start, valid_ticks, tick_duration, flag_prefix FROM scoring_gamecontrol')
        result = cursor.fetchone()

    if result is None:
        raise DBDataError('Game control information has not been configured')

    return {
        'contest_start': result[0],
        'valid_ticks': result[1],
        'tick_duration': result[2],
        'flag_prefix': result[3]
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


def get_service_margin(db_conn, service_slug, prohibit_changes=False):
    """
    Returns the configured safety margin of a service for a given slug.
    """

    with transaction_cursor(db_conn, prohibit_changes) as cursor:
        cursor.execute('SELECT margin FROM scoring_service WHERE slug = %s', (service_slug,))
        result = cursor.fetchone()

    if result is None:
        raise DBDataError('Service has not been configured')

    return result[0]


def get_current_tick(db_conn, prohibit_changes=False):
    """
    Reads the current tick and the "cancel_checks" field from the game database.
    """

    with transaction_cursor(db_conn, prohibit_changes) as cursor:
        cursor.execute('SELECT current_tick, cancel_checks FROM scoring_gamecontrol')
        result = cursor.fetchone()

    if result is None:
        raise DBDataError('Game control information has not been configured')

    return result


def get_check_duration(db_conn, service_id, std_dev_count, prohibit_changes=False):
    """
    Estimates the duration of checks for the given service from the average runtime of previous runs and its
    standard deviation. We include all previous runs to accomodate to Checker Scripts with varying runtimes.
    `std_dev_count` is the number of standard deviations to add to the average, i.e. increasing it will lead
    to a greater result. Assuming a normal distribution, 2 standard deviations will include ~ 95 % of
    previous results.
    """

    with transaction_cursor(db_conn, prohibit_changes) as cursor:
        cursor.execute('SELECT (avg(extract(epoch from (placement_end - placement_start))) + %s *'
                       '        stddev_pop(extract(epoch from (placement_end - placement_start))))::float'
                       '    FROM scoring_flag, scoring_gamecontrol'
                       '    WHERE service_id = %s AND tick < current_tick', (std_dev_count, service_id))
        result = cursor.fetchone()

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
        # We need a lock on the whole table to prevent deadlocks because of `ORDER BY RANDOM`
        # See https://github.com/fausecteam/ctf-gameserver/issues/62
        # "There is no UNLOCK TABLE command; locks are always released at transaction end"
        cursor.execute('LOCK TABLE scoring_flag IN EXCLUSIVE MODE')

        cursor.execute('SELECT flag.id, flag.protecting_team_id, flag.tick, team.net_number'
                       '    FROM scoring_flag flag, scoring_gamecontrol control, registration_team team'
                       '    WHERE flag.placement_start is NULL'
                       '        AND flag.tick = control.current_tick'
                       '        AND flag.service_id = %s'
                       '        AND flag.protecting_team_id = team.user_id'
                       '    ORDER BY RANDOM()'
                       '    LIMIT %s', (service_id, task_count))
        tasks = cursor.fetchall()

        # Mark placement as in progress
        cursor.executemany('UPDATE scoring_flag'
                           '    SET placement_start = NOW()'
                           '    WHERE id = %s', [(task[0],) for task in tasks])

    return [{
        'team_id': task[1],
        'team_net_no': task[3],
        'tick': task[2]
    } for task in tasks]


def get_flag_id(db_conn, service_id, team_id, tick, prohibit_changes=False, fake_flag_id=None):

    with transaction_cursor(db_conn, prohibit_changes) as cursor:
        cursor.execute('SELECT id FROM scoring_flag'
                       '    WHERE tick = %s'
                       '        AND service_id = %s'
                       '        AND protecting_team_id = %s', (tick, service_id, team_id))
        data = cursor.fetchone()
        if fake_flag_id is not None:
            data = (fake_flag_id,)
        return data[0]


def _net_no_to_team_id(cursor, team_net_no, fake_team_id):

    cursor.execute('SELECT user_id FROM registration_team WHERE net_number = %s', (team_net_no,))
    data = cursor.fetchone()

    # Only do this after executing the SQL query, because we want to ensure the query works
    if fake_team_id is not None:
        return fake_team_id
    elif data is None:
        return None

    return data[0]


def commit_result(db_conn, service_id, team_net_no, tick, result, prohibit_changes=False, fake_team_id=None):
    """
    Saves the result from a Checker run to game database.
    """

    with transaction_cursor(db_conn, prohibit_changes) as cursor:
        team_id = _net_no_to_team_id(cursor, team_net_no, fake_team_id)
        if team_id is None:
            logging.error('No team found with net number %d, cannot commit result', team_net_no)
            return

        cursor.execute('INSERT INTO scoring_statuscheck'
                       '    (service_id, team_id, tick, status, timestamp)'
                       '    VALUES (%s, %s, %s, %s, NOW())', (service_id, team_id, tick, result))
        if result != STATUS_TIMEOUT:
            # (In case of `prohibit_changes`,) PostgreSQL checks the database grants even if nothing is
            # matched by `WHERE`
            cursor.execute('UPDATE scoring_flag'
                           '    SET placement_end = NOW()'
                           '    WHERE service_id = %s AND protecting_team_id = %s AND tick = %s',
                           (service_id, team_id, tick))


def set_flagid(db_conn, service_id, team_net_no, tick, flagid, prohibit_changes=False, fake_team_id=None):
    """
    Stores a Flag ID in database.
    In case of conflict, the previous Flag ID gets overwritten.
    """

    with transaction_cursor(db_conn, prohibit_changes) as cursor:
        team_id = _net_no_to_team_id(cursor, team_net_no, fake_team_id)
        if team_id is None:
            logging.error('No team found with net number %d, cannot commit result', team_net_no)
            return

        # (In case of `prohibit_changes`,) PostgreSQL checks the database grants even if nothing is matched
        # by `WHERE`
        cursor.execute('UPDATE scoring_flag'
                       '    SET flagid = %s'
                       '    WHERE service_id = %s AND protecting_team_id = %s AND tick = %s', (flagid,
                                                                                               service_id,
                                                                                               team_id,
                                                                                               tick))


def load_state(db_conn, service_id, team_net_no, key, prohibit_changes=False):
    """
    Loads Checker state data from database.
    """

    with transaction_cursor(db_conn, prohibit_changes) as cursor:
        cursor.execute('SELECT data FROM scoring_checkerstate state, registration_team team'
                       '    WHERE state.service_id = %s'
                       '        AND state.key = %s'
                       '        AND team.net_number = %s'
                       '        AND state.team_id = team.user_id', (service_id, key, team_net_no))
        data = cursor.fetchone()

    if data is None:
        return None
    return data[0]


def store_state(db_conn, service_id, team_net_no, key, data, prohibit_changes=False, fake_team_id=None):
    """
    Stores Checker state data in database.
    """

    with transaction_cursor(db_conn, prohibit_changes) as cursor:
        team_id = _net_no_to_team_id(cursor, team_net_no, fake_team_id)
        if team_id is None:
            logging.error('No team found with net number %d, cannot store state', team_net_no)
            return

        # (In case of `prohibit_changes`,) PostgreSQL checks the database grants even if no CONFLICT occurs
        cursor.execute('INSERT INTO scoring_checkerstate (service_id, team_id, key, data)'
                       '    VALUES (%s, %s, %s, %s)'
                       '    ON CONFLICT (service_id, team_id, key)'
                       '        DO UPDATE SET data = EXCLUDED.data', (service_id, team_id, key, data))
