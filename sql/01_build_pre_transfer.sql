-- Builds tm.pre_transfer: one row per move from a Phase 1 source league into a top five league.
-- Every feature uses only data dated strictly before transfer_date. The label uses data after it.
-- Rules were fixed before any counts or model results were seen (see docs/decision_log.md, 2026-10-15).
-- Run: psql "$DATABASE_URL" -f sql/01_build_pre_transfer.sql

DROP SCHEMA IF EXISTS tm CASCADE;
CREATE SCHEMA tm;

CREATE TABLE tm.players AS
SELECT player_id::int AS player_id,
       name, position, sub_position, foot,
       nullif(height_in_cm,'')::numeric AS height_cm,
       nullif(date_of_birth,'')::timestamp::date AS dob,
       country_of_citizenship
FROM tm_raw.players;
CREATE UNIQUE INDEX ON tm.players(player_id);

CREATE TABLE tm.appearances AS
SELECT player_id::int AS player_id, player_club_id::int AS club_id, date::date AS d,
       competition_id, game_id::int AS game_id,
       coalesce(nullif(minutes_played,'')::int,0) AS minutes,
       coalesce(nullif(goals,'')::int,0) AS goals, coalesce(nullif(assists,'')::int,0) AS assists,
       coalesce(nullif(yellow_cards,'')::int,0) AS yellows, coalesce(nullif(red_cards,'')::int,0) AS reds
FROM tm_raw.appearances;
CREATE INDEX ON tm.appearances(player_id, d);
CREATE INDEX ON tm.appearances(club_id, competition_id, d);

CREATE TABLE tm.valuations AS
SELECT player_id::int AS player_id, date::date AS d, market_value_in_eur::numeric AS value_eur
FROM tm_raw.player_valuations;
CREATE INDEX ON tm.valuations(player_id, d);

-- One row per club per domestic first tier league game
CREATE TABLE tm.club_league_games AS
SELECT g.home_club_id::int AS club_id, g.date::date AS d, g.competition_id, g.game_id::int AS game_id
FROM tm_raw.games g JOIN tm_raw.competitions c ON c.competition_id = g.competition_id
WHERE c.type = 'domestic_league'
UNION ALL
SELECT g.away_club_id::int, g.date::date, g.competition_id, g.game_id::int
FROM tm_raw.games g JOIN tm_raw.competitions c ON c.competition_id = g.competition_id
WHERE c.type = 'domestic_league';
CREATE INDEX ON tm.club_league_games(club_id, d);

CREATE TABLE tm.funnel (step int, description text, n bigint);
INSERT INTO tm.funnel SELECT 1, 'rows in transfers table', count(*) FROM tm_raw.transfers;

CREATE TABLE tm.moves0 AS
SELECT row_number() OVER () AS move_id,
       player_id::int AS player_id, transfer_date::date AS transfer_date,
       from_club_id::int AS from_club_id, to_club_id::int AS to_club_id,
       from_club_name, to_club_name
FROM tm_raw.transfers
WHERE nullif(from_club_id,'') IS NOT NULL AND nullif(to_club_id,'') IS NOT NULL;

INSERT INTO tm.funnel SELECT 2, 'dated on or before snapshot 2026-07-06', count(*) FROM tm.moves0 WHERE transfer_date <= DATE '2026-07-06';
INSERT INTO tm.funnel SELECT 3, 'dated 2013-06-01 to 2024-09-30 (label window complete)', count(*) FROM tm.moves0
  WHERE transfer_date BETWEEN DATE '2013-06-01' AND DATE '2024-09-30';

-- League of each club at the time of the move, from games actually played.
-- From club: league of its most recent league game on or before the transfer date (within 400 days).
-- To club: league of its first league game on or after the transfer date (within 400 days).
CREATE TABLE tm.moves1 AS
SELECT m.*, f.competition_id AS from_league, t.competition_id AS to_league
FROM tm.moves0 m
LEFT JOIN LATERAL (SELECT competition_id FROM tm.club_league_games g
     WHERE g.club_id = m.from_club_id AND g.d <= m.transfer_date AND g.d > m.transfer_date - 400
     ORDER BY g.d DESC LIMIT 1) f ON true
LEFT JOIN LATERAL (SELECT competition_id FROM tm.club_league_games g
     WHERE g.club_id = m.to_club_id AND g.d >= m.transfer_date AND g.d < m.transfer_date + 400
     ORDER BY g.d ASC LIMIT 1) t ON true
WHERE m.transfer_date BETWEEN DATE '2013-06-01' AND DATE '2024-09-30';

INSERT INTO tm.funnel SELECT 4, 'from club in one of the 9 source leagues', count(*) FROM tm.moves1
  WHERE from_league IN ('BE1','NL1','PO1','TR1','SC1','DK1','GR1','RU1','UKR1');
INSERT INTO tm.funnel SELECT 5, 'and to club in a top five league (GB1 ES1 IT1 L1 FR1)', count(*) FROM tm.moves1
  WHERE from_league IN ('BE1','NL1','PO1','TR1','SC1','DK1','GR1','RU1','UKR1') AND to_league IN ('GB1','ES1','IT1','L1','FR1');

CREATE TABLE tm.moves2 AS
SELECT DISTINCT ON (player_id, transfer_date, to_club_id) *
FROM tm.moves1
WHERE from_league IN ('BE1','NL1','PO1','TR1','SC1','DK1','GR1','RU1','UKR1')
  AND to_league IN ('GB1','ES1','IT1','L1','FR1') AND from_club_id <> to_club_id
ORDER BY player_id, transfer_date, to_club_id, move_id;
INSERT INTO tm.funnel SELECT 6, 'after dropping same club moves and duplicate rows', count(*) FROM tm.moves2;

CREATE TABLE tm.pre_transfer AS
SELECT m.*,
  p.name AS player_name, p.position, p.sub_position, p.foot, p.height_cm, p.country_of_citizenship,
  (m.transfer_date - p.dob) / 365.25 AS age_at_transfer,
  (extract(month FROM m.transfer_date) BETWEEN 6 AND 9) AS summer_window,
  a.apps_365, a.minutes_365, a.goals_365, a.assists_365, a.yellows_365, a.reds_365,
  a.apps_90, a.minutes_90,
  b.minutes_prev365, b.apps_prev365,
  v.value_eur AS value_before, (m.transfer_date - v.d) AS value_age_days,
  v2.value_eur AS value_1y_before,
  l.minutes_y1, l.den_y1, l.minutes_y2, l.den_y2
FROM tm.moves2 m
JOIN tm.players p USING (player_id)
LEFT JOIN LATERAL (SELECT count(*) apps_365, sum(minutes) minutes_365, sum(goals) goals_365, sum(assists) assists_365,
      sum(yellows) yellows_365, sum(reds) reds_365,
      count(*) FILTER (WHERE d >= m.transfer_date - 90) apps_90,
      coalesce(sum(minutes) FILTER (WHERE d >= m.transfer_date - 90),0) minutes_90
   FROM tm.appearances x WHERE x.player_id = m.player_id AND x.d < m.transfer_date AND x.d >= m.transfer_date - 365) a ON true
LEFT JOIN LATERAL (SELECT count(*) apps_prev365, sum(minutes) minutes_prev365
   FROM tm.appearances x WHERE x.player_id = m.player_id AND x.d < m.transfer_date - 365 AND x.d >= m.transfer_date - 730) b ON true
LEFT JOIN LATERAL (SELECT value_eur, d FROM tm.valuations x WHERE x.player_id = m.player_id AND x.d < m.transfer_date ORDER BY x.d DESC LIMIT 1) v ON true
LEFT JOIN LATERAL (SELECT value_eur FROM tm.valuations x WHERE x.player_id = m.player_id AND x.d < m.transfer_date - 365 ORDER BY x.d DESC LIMIT 1) v2 ON true
-- LABEL inputs: league minutes at the new club versus minutes the club played, year 1 and year 2 after the move
LEFT JOIN LATERAL (SELECT
    (SELECT coalesce(sum(minutes),0) FROM tm.appearances x WHERE x.player_id = m.player_id AND x.club_id = m.to_club_id
        AND x.competition_id = m.to_league AND x.d >= m.transfer_date AND x.d < m.transfer_date + 365) minutes_y1,
    (SELECT count(*) * 90 FROM tm.club_league_games g WHERE g.club_id = m.to_club_id AND g.competition_id = m.to_league
        AND g.d >= m.transfer_date AND g.d < m.transfer_date + 365) den_y1,
    (SELECT coalesce(sum(minutes),0) FROM tm.appearances x WHERE x.player_id = m.player_id AND x.club_id = m.to_club_id
        AND x.competition_id = m.to_league AND x.d >= m.transfer_date + 365 AND x.d < m.transfer_date + 730) minutes_y2,
    (SELECT count(*) * 90 FROM tm.club_league_games g WHERE g.club_id = m.to_club_id AND g.competition_id = m.to_league
        AND g.d >= m.transfer_date + 365 AND g.d < m.transfer_date + 730) den_y2) l ON true;

ALTER TABLE tm.pre_transfer ADD COLUMN regular_starter int;
-- regular starter = in year 1 or year 2 after the move, played at least 50% of the possible league minutes
-- of the new club for that year (league games only, at the new club)
UPDATE tm.pre_transfer SET regular_starter =
  CASE WHEN (den_y1 > 0 AND minutes_y1 >= 0.5 * den_y1) OR (den_y2 > 0 AND minutes_y2 >= 0.5 * den_y2) THEN 1 ELSE 0 END;

INSERT INTO tm.funnel SELECT 7, 'pre transfer records with at least 1 appearance in the 365 days before the move', count(*) FROM tm.pre_transfer WHERE apps_365 >= 1;
CREATE TABLE tm.model_records AS SELECT * FROM tm.pre_transfer WHERE apps_365 >= 1;
