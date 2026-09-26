from ctf_gameserver.lib.database import transaction_cursor
from ctf_gameserver.lib.date_time import ensure_utc_aware
from ctf_gameserver.lib.exceptions import DBDataError


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
        cursor.execute('UPDATE scoring_gamecontrol SET current_tick = current_tick + 1,'
                       '                               cancel_checks = false')
        # Create checker tasks for every service and team in the new tick
        cursor.execute('INSERT INTO scoring_checkertask (service_id, team_id, tick)'
                       '    SELECT service.id, team.user_id, control.current_tick'
                       '    FROM scoring_service service, auth_user, registration_team team,'
                       '         scoring_gamecontrol control'
                       '    WHERE auth_user.id = team.user_id AND auth_user.is_active')
        # Create a flag for every flagstore of every newly created checker task
        cursor.execute('SELECT task.id, service.num_flagstores'
                       '    FROM scoring_checkertask task, scoring_service service,'
                       '         scoring_gamecontrol control'
                       '    WHERE task.service_id = service.id AND task.tick = control.current_tick')
        flag_rows = []
        for task_id, num_flagstores in cursor.fetchall():
            for flagstore in range(num_flagstores):
                flag_rows.append((task_id, flagstore))
        cursor.executemany('INSERT INTO scoring_flag (task_id, flagstore) VALUES (%s, %s)', flag_rows)


def cancel_checks(db_conn, prohibit_changes=False):

    with transaction_cursor(db_conn, prohibit_changes) as cursor:
        cursor.execute('UPDATE scoring_gamecontrol SET cancel_checks = true')


def get_exploiting_teams_counts(db_conn, prohibit_changes=False):

    with transaction_cursor(db_conn, prohibit_changes) as cursor:
        cursor.execute('SELECT service.slug, flag.flagstore, COUNT(DISTINCT capture.capturing_team_id)'
                       '    FROM scoring_service service'
                       '    JOIN scoring_checkertask task ON task.service_id = service.id'
                       '    JOIN scoring_flag flag ON flag.task_id = task.id'
                       '    LEFT JOIN (SELECT * FROM scoring_capture) AS capture'
                       '        ON capture.flag_id = flag.id'
                       '    GROUP BY service.slug, flag.flagstore')
        counts = cursor.fetchall()

    return {(c[0], c[1]): c[2] for c in counts}


def get_open_tasks_counts_cur(db_conn, prohibit_changes=False):

    task_where_clause = ('tick = (SELECT current_tick FROM scoring_gamecontrol) AND '
                         'exec_start IS NULL')
    return _get_task_counts(db_conn, task_where_clause, prohibit_changes)


def get_open_tasks_counts_old(db_conn, prohibit_changes=False):

    task_where_clause = ('tick != (SELECT current_tick FROM scoring_gamecontrol) AND '
                         'exec_start IS NULL')
    return _get_task_counts(db_conn, task_where_clause, prohibit_changes)


def get_incomplete_tasks_counts_cur(db_conn, prohibit_changes=False):

    task_where_clause = ('tick = (SELECT current_tick FROM scoring_gamecontrol) AND '
                         'exec_start IS NOT NULL AND exec_end IS NULL')
    return _get_task_counts(db_conn, task_where_clause, prohibit_changes)


def get_incomplete_tasks_counts_old(db_conn, prohibit_changes=False):

    task_where_clause = ('tick != (SELECT current_tick FROM scoring_gamecontrol) AND '
                         'exec_start IS NOT NULL AND exec_end IS NULL')
    return _get_task_counts(db_conn, task_where_clause, prohibit_changes)


def _get_task_counts(db_conn, task_where_clause, prohibit_changes):

    with transaction_cursor(db_conn, prohibit_changes) as cursor:
        cursor.execute('SELECT service.slug, COUNT(task.id)'    # nosec
                       '    FROM scoring_service service'
                       '    LEFT JOIN (SELECT * FROM scoring_checkertask WHERE {}) AS task'
                       '        ON task.service_id=service.id'
                       '    GROUP BY service.slug'.format(task_where_clause))
        counts = cursor.fetchall()

    return dict(counts)
