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
  sla_ok AS (
    SELECT count(*) as sla_ok,
           team_id,
           service_id
    FROM scoring_statuscheck
    WHERE status = 0
    GROUP BY team_id, service_id
  ),
  sla_recover AS (
    SELECT 0.5 * count(*) as sla_recover,
           team_id,
           service_id
    FROM scoring_statuscheck
    WHERE status = 4
    GROUP BY team_id, service_id
  ),
  teams as (
    SELECT user_id as team_id
    FROM registration_team
    INNER JOIN auth_user ON auth_user.id = registration_team.user_id
    WHERE is_active = true
	  AND nop_team = false
  ),
  sla AS (
    SELECT (SELECT sqrt(count(*)) FROM teams) * (coalesce(sla_ok, 0) + coalesce(sla_recover, 0)) as sla,
           team_id,
           service_id
    FROM sla_ok
    NATURAL FULL OUTER JOIN sla_recover
  ),
  fill AS (
    SELECT team_id, scoring_service.id AS service_id
    FROM teams, scoring_service
  )
SELECT team_id,
       service_id,
       (coalesce(attack, 0)+coalesce(bonus, 0))::double precision as attack,
       coalesce(bonus, 0) as bonus,
       coalesce(defense, 0)::double precision as defense,
       coalesce(sla, 0) as sla,
       coalesce(attack, 0) + coalesce(defense, 0) + coalesce(bonus, 0) + coalesce(sla, 0) as total
FROM attack
NATURAL FULL OUTER JOIN defense
NATURAL FULL OUTER JOIN sla
NATURAL INNER JOIN fill
ORDER BY team_id, service_id;

ALTER MATERIALIZED VIEW scoring_scoreboard OWNER TO gameserver_controller;
GRANT SELECT on TABLE scoring_scoreboard TO gameserver_web;
