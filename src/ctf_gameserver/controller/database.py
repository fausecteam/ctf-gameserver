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
        # Create flags for every service and team in the new tick
        cursor.execute('INSERT INTO scoring_flag (service_id, protecting_team_id, tick)'
                       '    SELECT service.id, team.user_id, control.current_tick'
                       '    FROM scoring_service service, auth_user, registration_team team,'
                       '         scoring_gamecontrol control'
                       '    WHERE auth_user.id = team.user_id AND auth_user.is_active')


def cancel_checks(db_conn, prohibit_changes=False):

    with transaction_cursor(db_conn, prohibit_changes) as cursor:
        cursor.execute('UPDATE scoring_gamecontrol SET cancel_checks = true')


def get_exploiting_teams_counts(db_conn, prohibit_changes=False):

    with transaction_cursor(db_conn, prohibit_changes) as cursor:
        cursor.execute('SELECT service.slug, COUNT(DISTINCT capture.capturing_team_id)'
                       '    FROM scoring_service service'
                       '    JOIN scoring_flag flag ON flag.service_id = service.id'
                       '    LEFT JOIN (SELECT * FROM scoring_capture) AS capture'
                       '        ON capture.flag_id = flag.id'
                       '    GROUP BY service.slug')
        counts = cursor.fetchall()

    return dict(counts)


def get_unplaced_flags_counts_cur(db_conn, prohibit_changes=False):

    flag_where_clause = ('tick = (SELECT current_tick FROM scoring_gamecontrol) AND '
                         'placement_start IS NULL')
    return _get_flags_counts(db_conn, flag_where_clause, prohibit_changes)


def get_unplaced_flags_counts_old(db_conn, prohibit_changes=False):

    flag_where_clause = ('tick != (SELECT current_tick FROM scoring_gamecontrol) AND '
                         'placement_start IS NULL')
    return _get_flags_counts(db_conn, flag_where_clause, prohibit_changes)


def get_incomplete_flags_counts_cur(db_conn, prohibit_changes=False):

    flag_where_clause = ('tick = (SELECT current_tick FROM scoring_gamecontrol) AND '
                         'placement_start IS NOT NULL AND placement_end IS NULL')
    return _get_flags_counts(db_conn, flag_where_clause, prohibit_changes)


def get_incomplete_flags_counts_old(db_conn, prohibit_changes=False):

    flag_where_clause = ('tick != (SELECT current_tick FROM scoring_gamecontrol) AND '
                         'placement_start IS NOT NULL AND placement_end IS NULL')
    return _get_flags_counts(db_conn, flag_where_clause, prohibit_changes)


def _get_flags_counts(db_conn, flag_where_clause, prohibit_changes):

    with transaction_cursor(db_conn, prohibit_changes) as cursor:
        cursor.execute('SELECT service.slug, COUNT(flag.id)'    # nosec
                       '    FROM scoring_service service'
                       '    LEFT JOIN (SELECT * FROM scoring_flag WHERE {}) AS flag'
                       '        ON flag.service_id=service.id'
                       '    GROUP BY service.slug'.format(flag_where_clause))
        counts = cursor.fetchall()

    return dict(counts)
