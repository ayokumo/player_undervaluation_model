-- One row per player, club and season in the nine source leagues (league games only), seasons 2022/23 to 2025/26.
-- Source: Transfermarkt snapshot 2026-07-06 (tm_raw). Season label is the start year, verified against games.season.
-- Run after sql/01 (needs the tm schema).
DROP TABLE IF EXISTS tm.player_season_stats;
CREATE TABLE tm.player_season_stats AS
WITH lg(code, league_name) AS (VALUES
  ('BE1','Belgian Pro League'),('NL1','Eredivisie'),('PO1','Liga Portugal'),('TR1','Turkish Super Lig'),
  ('SC1','Scottish Premiership'),('DK1','Danish Superliga'),('GR1','Greek Super League'),
  ('RU1','Russian Premier League'),('UKR1','Ukrainian Premier League')),
a AS (
  SELECT x.player_id, x.club_id, x.competition_id,
         CASE WHEN extract(month FROM x.d) >= 7 THEN extract(year FROM x.d)::int ELSE extract(year FROM x.d)::int - 1 END AS season_start,
         x.minutes, x.goals, x.assists, x.yellows, x.reds
  FROM tm.appearances x JOIN lg ON lg.code = x.competition_id
  WHERE x.d >= DATE '2022-07-01'
),
agg AS (
  SELECT player_id, club_id, competition_id AS league, season_start,
         count(*) AS apps, sum(minutes) AS minutes, sum(goals) AS goals, sum(assists) AS assists,
         sum(yellows) AS yellows, sum(reds) AS reds
  FROM a GROUP BY 1,2,3,4
)
SELECT g.player_id, p.name AS name,
       g.season_start::text || '/' || lpad(((g.season_start + 1) % 100)::text, 2, '0') AS season,
       g.season_start,
       CASE
         WHEN pl.sub_position IN ('Left Winger','Right Winger','Left Midfield','Right Midfield') THEN 'winger'
         WHEN pl.sub_position IN ('Centre-Forward','Second Striker') THEN 'striker'
         WHEN pl.sub_position = 'Attacking Midfield' THEN 'attacking_mid'
         WHEN pl.sub_position IN ('Central Midfield','Defensive Midfield') THEN 'central_mid'
         WHEN pl.sub_position IN ('Centre-Back','Right-Back','Left-Back') THEN 'defender'
         WHEN pl.sub_position = 'Goalkeeper' THEN 'goalkeeper'
         WHEN pl.position = 'Attack' THEN 'striker'
         WHEN pl.position = 'Midfield' THEN 'central_mid'
         WHEN pl.position = 'Defender' THEN 'defender'
         WHEN pl.position = 'Goalkeeper' THEN 'goalkeeper'
       END AS position_group,
       g.league, lg.league_name, c.name AS club,
       floor((make_date(g.season_start, 8, 1) - p.dob) / 365.25)::int AS age,
       g.apps, g.minutes, g.goals, g.assists, g.yellows, g.reds,
       round(g.goals * 90.0 / g.minutes, 3) AS goals_p90,
       round(g.assists * 90.0 / g.minutes, 3) AS assists_p90,
       round((g.goals + g.assists) * 90.0 / g.minutes, 3) AS goal_contrib_p90,
       round(g.yellows * 90.0 / g.minutes, 3) AS yellows_p90,
       round(g.minutes * 1.0 / g.apps, 1) AS minutes_per_app,
       v.value_eur AS market_value_eur,
       p.country_of_citizenship AS nationality
FROM agg g
JOIN lg ON lg.code = g.league
JOIN tm.players p ON p.player_id = g.player_id
JOIN tm_raw.players pl ON pl.player_id::int = g.player_id
JOIN tm_raw.clubs c ON c.club_id::int = g.club_id
LEFT JOIN LATERAL (SELECT value_eur FROM tm.valuations v WHERE v.player_id = g.player_id
     AND v.d <= make_date(g.season_start + 1, 6, 30) ORDER BY v.d DESC LIMIT 1) v ON true
WHERE g.minutes >= 900 AND g.season_start BETWEEN 2022 AND 2025 AND p.dob IS NOT NULL;
ALTER TABLE tm.player_season_stats ADD COLUMN doc_id text GENERATED ALWAYS AS (player_id::text || '_' || season || '_' || club) STORED;
CREATE INDEX ON tm.player_season_stats(league, season, position_group);
