DROP TABLE IF EXISTS "scoring_scoreboard";
DROP MATERIALIZED VIEW IF EXISTS "scoring_scoreboard";

-- Scoreboard
CREATE MATERIALIZED VIEW "scoring_scoreboard" AS
WITH
  attack AS (
    SELECT capturing_team_id as team_id,
           service_id,
           count(*) as attack,
           sum(bonus) as bonus
    FROM scoring_capture
    INNER JOIN scoring_flag ON scoring_capture.flag_id = scoring_flag.id
    GROUP BY capturing_team_id, service_id
  ),
  flagdefense AS (
    SELECT count(*) ^ 0.75 as score,
           scoring_flag.protecting_team_id as team_id,
           service_id
    FROM scoring_capture
    INNER JOIN scoring_flag ON scoring_capture.flag_id = scoring_flag.id
    GROUP BY scoring_flag.id, service_id
  ),
  defense AS (
    SELECT -sum(score) as defense,
           team_id,
           service_id
    FROM flagdefense
    GROUP BY team_id, service_id
  ),
--  sla_ok AS (
--    SELECT count(*) as sla_ok,
--           team_id,
--           service_id
--    FROM scoring_statuscheck
--    WHERE status = 0
--    GROUP BY team_id, service_id
--  ),
--  sla_recover AS (
--    SELECT 0.5 * count(*) as sla_recover,
--           team_id,
--           service_id
--    FROM scoring_statuscheck
--    WHERE status = 4
--    GROUP BY team_id, service_id
--  ),
  teams as (
    SELECT user_id as team_id
    FROM registration_team
    INNER JOIN auth_user ON auth_user.id = registration_team.user_id
    WHERE is_active = true
	  AND nop_team = false
  ),
--  sla AS (
--    SELECT (SELECT sqrt(count(*)) FROM teams) * (coalesce(sla_ok, 0) + coalesce(sla_recover, 0)) as sla,
--           team_id,
--           service_id
--    FROM sla_ok
--    NATURAL FULL OUTER JOIN sla_recover
--  ),
  fill AS (
    SELECT team_id, scoring_servicegroup.id AS service_group_id
    FROM teams, scoring_servicegroup
  ),
  servicegroup AS (
    SELECT scoring_service.service_group_id AS service_group_id,
           count(scoring_service.id) AS services_count
    FROM scoring_service
    GROUP BY scoring_service.service_group_id
  ),
  attack_by_servicegroup AS (
    SELECT team_id,
           scoring_service.service_group_id AS service_group_id,
           sum(attack) AS attack,
           sum(bonus) AS bonus
    FROM attack
    INNER JOIN scoring_service ON scoring_service.id = attack.service_id
    GROUP BY team_id, scoring_service.service_group_id
  ),
  defense_by_servicegroup AS (
    SELECT team_id,
           scoring_service.service_group_id AS service_group_id,
           sum(defense) AS defense
    FROM defense
    INNER JOIN scoring_service ON scoring_service.id = defense.service_id
    GROUP BY team_id, scoring_service.service_group_id
  ),
  sla_ok_by_servicegroup_tick AS (
    SELECT team_id,
           scoring_service.service_group_id AS service_group_id,
           0.5 * servicegroup.services_count * (COUNT(*) = servicegroup.services_count)::int AS sla_ok
    FROM scoring_statuscheck
    INNER JOIN scoring_service ON scoring_service.id = scoring_statuscheck.service_id
    INNER JOIN servicegroup ON servicegroup.service_group_id = scoring_service.service_group_id
    WHERE scoring_statuscheck.status = 0
    GROUP BY team_id, scoring_service.service_group_id, servicegroup.services_count, scoring_statuscheck.tick
  ),
  sla_ok_by_servicegroup AS (
    SELECT team_id,
           service_group_id,
           sum(sla_ok) AS sla_ok
    FROM sla_ok_by_servicegroup_tick
    GROUP BY team_id, service_group_id
  ),
  sla_recover_by_servicegroup_tick AS (
    SELECT team_id,
           scoring_service.service_group_id AS service_group_id,
           0.5 * servicegroup.services_count * (COUNT(*) = servicegroup.services_count)::int AS sla_recover
    FROM scoring_statuscheck
    INNER JOIN scoring_service ON scoring_service.id = scoring_statuscheck.service_id
    INNER JOIN servicegroup ON servicegroup.service_group_id = scoring_service.service_group_id
    WHERE scoring_statuscheck.status = 4 OR scoring_statuscheck.status = 0
    GROUP BY team_id, scoring_service.service_group_id, servicegroup.services_count, scoring_statuscheck.tick
  ),
  sla_recover_by_servicegroup AS (
    SELECT team_id,
           service_group_id,
           sum(sla_recover) AS sla_recover
    FROM sla_recover_by_servicegroup_tick
    GROUP BY team_id, service_group_id
  ),
  sla_by_servicegroup AS (
    SELECT (SELECT sqrt(count(*)) FROM teams) * (coalesce(sla_ok, 0) + coalesce(sla_recover, 0)) as sla,
           team_id,
           service_group_id
    FROM sla_ok_by_servicegroup
    NATURAL FULL OUTER JOIN sla_recover_by_servicegroup
--  ),
--  sla_by_servicegroup AS ( -- alternative sla without interplay between servicegroups
--    SELECT team_id,
--           scoring_service.service_group_id AS service_group_id,
--           sum(sla) AS sla
--    FROM sla
--    INNER JOIN scoring_service ON scoring_service.id = sla.service_id
--    GROUP BY team_id, scoring_service.service_group_id
  )
SELECT team_id,
       service_group_id,
       (coalesce(attack, 0)+coalesce(bonus, 0))::double precision as attack,
       coalesce(bonus, 0) as bonus,
       coalesce(defense, 0)::double precision as defense,
       coalesce(sla, 0) as sla,
       coalesce(attack, 0) + coalesce(defense, 0) + coalesce(bonus, 0) + coalesce(sla, 0) as total
FROM attack_by_servicegroup
NATURAL FULL OUTER JOIN defense_by_servicegroup
NATURAL FULL OUTER JOIN sla_by_servicegroup
NATURAL INNER JOIN fill
ORDER BY team_id, service_group_id;
