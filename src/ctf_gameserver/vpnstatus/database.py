from ctf_gameserver.lib.database import transaction_cursor


def get_active_teams(db_conn):
    """
    Returns active teams as tuples of (user) ID and net number.
    """

    with transaction_cursor(db_conn) as cursor:
        cursor.execute('SELECT auth_user.id, team.net_number FROM auth_user, registration_team team'
                       '    WHERE auth_user.id = team.user_id AND auth_user.is_active')
        result = cursor.fetchall()

    return result


def add_results(db_conn, results_dict, prohibit_changes=False):
    """
    Stores all check results for all teams in the database. Expects the results as a nested dict with team
    IDs as outer keys and kinds of checks as inner keys.
    """

    with transaction_cursor(db_conn, prohibit_changes) as cursor:
        rows = []
        for team_id, team_results in results_dict.items():
            rows.append((team_id, team_results['wireguard_handshake_time'],
                         team_results['gateway_ping_rtt_ms'], team_results['demo_ping_rtt_ms'],
                         team_results['demo_service_ok'], team_results['vulnbox_ping_rtt_ms'],
                         team_results['vulnbox_service_ok']))

        cursor.executemany('INSERT INTO vpnstatus_vpnstatuscheck (team_id, wireguard_handshake_time,'
                           '    gateway_ping_rtt_ms, demo_ping_rtt_ms, demo_service_ok, vulnbox_ping_rtt_ms,'
                           '    vulnbox_service_ok, timestamp)'
                           'VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())', rows)
