from collections import defaultdict
import math

from ctf_gameserver.lib.checkresult import CheckResult
from ctf_gameserver.lib.database import transaction_cursor


def calculate_scoreboard(db_conn, prohibit_changes=False):

    # Attack/offensive scores by team ID and then service ID
    team_attack = {}
    # Defense scores by team ID and then service ID
    team_defense = {}
    # SLA scores by team ID and then service ID
    team_sla = {}

    # Total number of captures by flag ID
    flag_capture_counts = defaultdict(lambda: 0)

    with transaction_cursor(db_conn, prohibit_changes) as cursor:
        cursor.execute('SELECT user_id FROM registration_team WHERE nop_team = true')
        nop_team_ids = set(t[0] for t in cursor.fetchall())

        cursor.execute('SELECT f.service_id, c.capturing_team_id, f.protecting_team_id, f.id'
                       '    FROM scoring_capture c, scoring_flag f WHERE c.flag_id = f.id')
        # The submission server does not prevent NOP teams from submitting flags, even though it usually
        # shouldn't happen
        captures = [c for c in cursor.fetchall() if c[1] not in nop_team_ids]

        cursor.execute('SELECT id, service_id, protecting_team_id FROM scoring_flag')
        flags = [f for f in cursor.fetchall() if f[2] not in nop_team_ids]

        service_ids = set(f[1] for f in flags)
        team_ids = set(f[2] for f in flags)

        # Pre-fill the dicts (instead of using defaultdicts) to have values wherever they are required
        for team_id in team_ids:
            team_attack[team_id] = {i: 0.0 for i in service_ids}
            team_defense[team_id] = {i: 0.0 for i in service_ids}
            team_sla[team_id] = {i: 0.0 for i in service_ids}

        # Attack scoring
        for service_id, team_id, _, flag_id in captures:
            flag_capture_counts[flag_id] += 1
            team_attack[team_id][service_id] += 1

        for service_id, capturing_team_id, protecting_team_id, flag_id in captures:
            team_attack[capturing_team_id][service_id] += 1.0 / flag_capture_counts[flag_id]

        # Defense scoring
        for flag_id, service_id, protecting_team_id in flags:
            # The submission server *does* prevent submitting flags protected by NOP teams
            team_defense[protecting_team_id][service_id] -= flag_capture_counts[flag_id] ** 0.75

        # SLA scoring
        cursor.execute('SELECT COUNT(*) FROM registration_team t, auth_user u'
                       '    WHERE t.user_id = u.id AND u.is_active = true AND t.nop_team = false')
        team_count = cursor.fetchone()[0]

        checks_select = ('SELECT team_id, service_id, COUNT(*) FROM scoring_statuscheck'
                         '    WHERE status = %s GROUP BY team_id, service_id')
        cursor.execute(checks_select, (CheckResult.OK.value,))
        ok_checks = [c for c in cursor.fetchall() if c[0] not in nop_team_ids]
        cursor.execute(checks_select, (CheckResult.RECOVERING.value,))
        recovering_checks = [c for c in cursor.fetchall() if c[0] not in nop_team_ids]

        for team_id, service_id, tick_count in ok_checks:
            team_sla[team_id][service_id] += tick_count
        for team_id, service_id, tick_count in recovering_checks:
            team_sla[team_id][service_id] += 0.5 * tick_count

        sla_factor = math.sqrt(team_count)

        for team_id, service_sla in team_sla.items():
            for service_id in service_sla:
                service_sla[service_id] *= sla_factor

        row_values = []

        for team_id, service_attack in team_attack.items():
            for service_id in service_attack:
                # pylint: disable=unnecessary-dict-index-lookup
                attack = team_attack[team_id][service_id]
                defense = team_defense[team_id][service_id]
                sla = team_sla[team_id][service_id]
                total = attack + defense + sla
                row_values.append((team_id, service_id, attack, defense, sla, total))

        cursor.execute('DELETE FROM scoring_scoreboard')
        cursor.executemany('INSERT INTO scoring_scoreboard'
                           '    (team_id, service_id, attack, defense, sla, total)'
                           '    VALUES (%s, %s, %s, %s, %s, %s)', row_values)
