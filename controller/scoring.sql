-- Update bonus
UPDATE scoring_flag as outerflag
SET bonus = 1 / (
  SELECT greatest(1, count(*))
  FROM scoring_flag
  LEFT OUTER JOIN scoring_capture ON scoring_capture.flag_id = scoring_flag.id
  WHERE scoring_capture.flag_id = outerflag.id)
FROM scoring_gamecontrol
WHERE outerflag.tick + scoring_gamecontrol.valid_ticks < scoring_gamecontrol.current_tick
  AND outerflag.bonus IS NULL;

-- Scoreboard
CREATE MATERIALIZED VIEW "scoring_scoreboard" AS
WITH
  attack AS (
    SELECT capturing_team_id as team_id,
           count(*) as attack,
           sum(bonus) as bonus
    FROM scoring_capture
    INNER JOIN scoring_flag ON scoring_capture.flag_id = scoring_flag.id
    GROUP BY capturing_team_id
  ),
  flagdefense AS (
    SELECT sqrt(count(*)) as score,
           scoring_flag.protecting_team_id as team_id
    FROM scoring_capture
    INNER JOIN scoring_flag ON scoring_capture.flag_id = scoring_flag.id
    GROUP BY scoring_flag.id
  ),
  defense AS (
    SELECT -sum(score) as defense,
           team_id
    FROM flagdefense
    GROUP BY team_id
  ),
  sla_ok AS (
    SELECT count(*) as sla_ok,
           team_id
    FROM scoring_statuscheck
    WHERE status = 0
    GROUP BY team_id
  ),
  sla_recover AS (
    SELECT 0.5 * count(*) as sla_recover,
           team_id
    FROM scoring_statuscheck
    WHERE status = 4
    GROUP BY team_id
  ),
  teams as (
    SELECT count(*) as teams
    FROM registration_team
    INNER JOIN auth_user ON auth_user.id = registration_team.user_id
    WHERE is_active = true
  ),
  sla AS (
    SELECT (SELECT sqrt(teams) FROM teams) * (coalesce(sla_ok, 0) + coalesce(sla_recover, 0)) as sla,
           team_id
    FROM sla_ok
    NATURAL FULL OUTER JOIN sla_recover
  )
SELECT team_id,
       coalesce(attack, 0)::double precision as attack,
       coalesce(bonus, 0) as bonus,
       coalesce(defense, 0) as defense,
       sla,
       coalesce(attack, 0) + coalesce(defense, 0) + coalesce(bonus, 0) + sla as total
FROM attack
NATURAL FULL OUTER JOIN defense
NATURAL FULL OUTER JOIN sla
ORDER BY team_id;
