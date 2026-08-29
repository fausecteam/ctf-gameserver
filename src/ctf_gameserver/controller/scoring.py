from collections import defaultdict
import math

from ctf_gameserver.lib.checkresult import CheckResult
from ctf_gameserver.lib.database import transaction_cursor


# Adjustable factor applied to attack and defense scores of services with more than one flagstore
MULTI_FLAGSTORE_FACTOR = 0.7


def calculate_scoreboard(db_conn, prohibit_changes=False):

    # Attack/offensive scores by team ID, then service ID, then flagstore
    team_attack = {}
    # Defense scores by team ID, then service ID, then flagstore
    team_defense = {}
    # SLA scores by team ID and then service ID
    team_sla = {}

    # Total number of captures by flag ID
    flag_capture_counts = defaultdict(lambda: 0)

    with transaction_cursor(db_conn, prohibit_changes) as cursor:
        cursor.execute('SELECT user_id FROM registration_team WHERE nop_team = true')
        nop_team_ids = set(t[0] for t in cursor.fetchall())

        cursor.execute('SELECT id, num_flagstores FROM scoring_service')
        service_num_flagstores = dict(cursor.fetchall())

        cursor.execute('SELECT t.service_id, c.capturing_team_id, t.team_id, f.id, f.flagstore'
                       '    FROM scoring_capture c, scoring_flag f, scoring_checkertask t'
                       '    WHERE c.flag_id = f.id AND f.task_id = t.id')
        # The submission server does not prevent NOP teams from submitting flags, even though it usually
        # shouldn't happen
        captures = [c for c in cursor.fetchall() if c[1] not in nop_team_ids]

        cursor.execute('SELECT f.id, t.service_id, t.team_id, f.flagstore'
                       '    FROM scoring_flag f, scoring_checkertask t'
                       '    WHERE f.task_id = t.id')
        flags = [f for f in cursor.fetchall() if f[2] not in nop_team_ids]

        service_ids = set(f[1] for f in flags)
        team_ids = set(f[2] for f in flags)

        # Factor applied per service to attack and defense; single-flagstore services stay unaffected
        service_factors = {service_id: MULTI_FLAGSTORE_FACTOR
                           if service_num_flagstores[service_id] > 1 else 1.0
                           for service_id in service_ids}

        # Pre-fill the dicts (instead of using defaultdicts) to have values wherever they are required
        for team_id in team_ids:
            team_attack[team_id] = {service_id: {flagstore: 0.0
                                                 for flagstore in range(service_num_flagstores[service_id])}
                                    for service_id in service_ids}
            team_defense[team_id] = {service_id: {flagstore: 0.0
                                                  for flagstore in range(service_num_flagstores[service_id])}
                                     for service_id in service_ids}
            team_sla[team_id] = {i: 0.0 for i in service_ids}

        # Attack scoring
        for service_id, capturing_team_id, _, flag_id, flagstore in captures:
            flag_capture_counts[flag_id] += 1
            team_attack[capturing_team_id][service_id][flagstore] += 1

        for service_id, capturing_team_id, _, flag_id, flagstore in captures:
            team_attack[capturing_team_id][service_id][flagstore] += 1.0 / flag_capture_counts[flag_id]

        # Defense scoring
        for flag_id, service_id, protecting_team_id, flagstore in flags:
            # The submission server *does* prevent submitting flags protected by NOP teams
            team_defense[protecting_team_id][service_id][flagstore] -= flag_capture_counts[flag_id] ** 0.75

        # SLA scoring
        cursor.execute('SELECT COUNT(*) FROM registration_team t, auth_user u'
                       '    WHERE t.user_id = u.id AND u.is_active = true AND t.nop_team = false')
        team_count = cursor.fetchone()[0]

        checks_select = ('SELECT t.team_id, t.service_id, COUNT(*)'
                         '    FROM scoring_statuscheck c, scoring_checkertask t'
                         '    WHERE c.task_id = t.id AND c.status = %s'
                         '    GROUP BY t.team_id, t.service_id')
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
                factor = service_factors[service_id]
                store_attack = team_attack[team_id][service_id]
                store_defense = team_defense[team_id][service_id]
                aggregate_attack = 0.0
                aggregate_defense = 0.0
                # Per-store rows carry the factored per-store attack/defense, no SLA and no total
                for flagstore in range(service_num_flagstores[service_id]):
                    attack = store_attack[flagstore] * factor
                    defense = store_defense[flagstore] * factor
                    aggregate_attack += attack
                    aggregate_defense += defense
                    row_values.append((team_id, service_id, flagstore, attack, defense, 0.0, 0.0))
                # Aggregate row (flagstore NULL): Factored attack/defense summed over stores plus per-service
                # SLA
                sla = team_sla[team_id][service_id]
                total = aggregate_attack + aggregate_defense + sla
                row_values.append((team_id, service_id, None, aggregate_attack, aggregate_defense, sla,
                                   total))

        cursor.execute('DELETE FROM scoring_scoreboard')
        cursor.executemany('INSERT INTO scoring_scoreboard'
                           '    (team_id, service_id, flagstore, attack, defense, sla, total)'
                           '    VALUES (%s, %s, %s, %s, %s, %s, %s)', row_values)
