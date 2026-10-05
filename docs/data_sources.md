# Data Sources

## Transfermarkt datasets (dcaribou)
Source: https://www.kaggle.com/datasets/davidcariboo/player-scores
GitHub: https://github.com/dcaribou/transfermarkt-datasets
License: CC0 1.0 (repo). Underlying data scraped from Transfermarkt.
Snapshot: current to 2026-07-06. Updates paused mid July 2026.
  games: nothing after 2026-07-06
  appearances: nothing after 2026-06-28
  player_valuations: nothing after 2026-06-12
Downloaded: 2026-09-25
Location: data/raw/transfermarkt/2026_07_06/ (gitignored, never edited)
Files: appearances, club_games, clubs, competitions, countries, game_events,
  game_lineups, games, national_teams, player_valuations, players, transfers (.csv)

### Verified coverage (games table, 2026-09-25)
Full history 2012 to 2025 (14 seasons):
  Top five: GB1, ES1, IT1, L1, FR1
  Phase 1 sources: BE1, NL1, PO1, TR1, SC1, DK1, GR1, RU1, UKR1
Only 2024 to 2025: ARG1, BRA1, A1, C1, KR1, PL1, SE1, NO1, SER1, TS1, RO1,
  MLS1, MEX1, SA1, AUS1, RSK1; JAP1 and COL1 one season only.
Season labels assumed to be start year (2012 = 2012/13). UNVERIFIED.

### Known issues (transfers table, 175,165 rows)
Date range: 1993-07-01 to 2030-06-30.
Future dated (after 2026-07-06): 520 rows. Dropped.
transfer_fee: 61,526 null, 96,085 zero. Null = unknown, not zero.
clubs.domestic_competition_id is the CURRENT league, not historical.

### Not usable / removed sources
FBref advanced stats: removed Jan 2026 (StatsPerform ended its data feed). Basic stats only remain.
