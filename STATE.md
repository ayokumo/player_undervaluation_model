DATE: 2026-10-05
CURRENT STAGE: 0 (Scoping and setup), closing
LAST THING COMPLETED: Repo, environment, data download, coverage check, decision log, README
WHAT I'M WORKING ON NOW: Committing Stage 0, then Stage 1 (src/ingest.py and raw profiling)

SCOPE
  Source league(s): BE1, NL1, PO1, TR1, SC1, DK1, GR1, RU1, UKR1 (Phase 1)
  Destination league(s): GB1, ES1, IT1, L1, FR1
  Seasons: stats 2012/13 to 2025/26; labeled transfers summer 2013 to summer 2024; 2025+ score only
  Positions: all

DATA SOURCES (verified? date checked):
  dcaribou transfermarkt-datasets, snapshot 2026-07-06, downloaded 2026-09-25
  Repo license CC0 1.0; Kaggle page license not confirmed
  League and season coverage verified from games table 2026-09-25
  Season label convention (2012 = 2012/13) UNVERIFIED

KEY NUMBERS
  Players in raw data: UNKNOWN
  Match rate across sources: N/A (single source, shared player_id)
  Labeled transfers (success / failure): N/A
  Train period / test period: N/A
  Best model + test metrics: N/A
  Baseline metrics: N/A
  Transfers table: 175,165 rows, 520 future dated
  Rough movers into top five from the 9 sources: about 2,896 (uses current club league, unverified)

DECISION LOG (latest entries):
  Phased scope; dcaribou data source; Python 3.14.3 venv; Phase 1 source leagues;
  season window; fees not used as feature or label; destination leagues; snapshot cutoff 2026-07-06

OPEN PROBLEMS / BUGS:
  Season label convention unverified
  clubs.domestic_competition_id is current league, not league at transfer time
  Fee zero vs null semantics not yet understood
  Phase 2 (South America) has no historical data source yet

QUESTIONS FOR THIS SESSION:
  None

PASTED BELOW:
  Stage 0 audit output (git status, git log, git ls-files, README, decision log)