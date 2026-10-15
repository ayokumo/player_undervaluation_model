-- Features for players currently in the nine source leagues, as of the snapshot date 2026-07-06.
-- Same definitions as sql/01 (only data dated before the as-of date). Run after 01.
DROP TABLE IF EXISTS tm.shortlist_features;
CREATE TABLE tm.shortlist_features AS
SELECT p.player_id, p.name AS player_name, p.position, p.sub_position, p.foot, p.height_cm,
  pr.current_club_id::int AS club_id, pr.current_club_name AS club_name,
  pr.current_club_domestic_competition_id AS from_league,
  DATE '2026-07-06' AS transfer_date,
  (DATE '2026-07-06' - p.dob) / 365.25 AS age_at_transfer,
  true AS summer_window,
  a.apps_365, a.minutes_365, a.goals_365, a.assists_365, a.yellows_365, a.reds_365, a.apps_90, a.minutes_90,
  b.minutes_prev365, b.apps_prev365,
  v.value_eur AS value_before, (DATE '2026-07-06' - v.d) AS value_age_days, v2.value_eur AS value_1y_before
FROM tm_raw.players pr
JOIN tm.players p ON p.player_id = pr.player_id::int
LEFT JOIN LATERAL (SELECT count(*) apps_365, sum(minutes) minutes_365, sum(goals) goals_365, sum(assists) assists_365,
      sum(yellows) yellows_365, sum(reds) reds_365,
      count(*) FILTER (WHERE d >= DATE '2026-07-06' - 90) apps_90,
      coalesce(sum(minutes) FILTER (WHERE d >= DATE '2026-07-06' - 90),0) minutes_90
   FROM tm.appearances x WHERE x.player_id = p.player_id AND x.d < DATE '2026-07-06' AND x.d >= DATE '2026-07-06' - 365) a ON true
LEFT JOIN LATERAL (SELECT count(*) apps_prev365, sum(minutes) minutes_prev365
   FROM tm.appearances x WHERE x.player_id = p.player_id AND x.d < DATE '2026-07-06' - 365 AND x.d >= DATE '2026-07-06' - 730) b ON true
LEFT JOIN LATERAL (SELECT value_eur, d FROM tm.valuations x WHERE x.player_id = p.player_id AND x.d < DATE '2026-07-06' ORDER BY x.d DESC LIMIT 1) v ON true
LEFT JOIN LATERAL (SELECT value_eur FROM tm.valuations x WHERE x.player_id = p.player_id AND x.d < DATE '2026-07-06' - 365 ORDER BY x.d DESC LIMIT 1) v2 ON true
WHERE pr.current_club_domestic_competition_id IN ('BE1','NL1','PO1','TR1','SC1','DK1','GR1','RU1','UKR1')
  AND pr.last_season::int >= 2025;
