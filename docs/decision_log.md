# Decision Log

## 2026-09-25: Phased scope
Decision: Phase 1 = European non top five leagues to top five leagues, all positions.
Phase 2 = add South America (scraping). Phase 3 = advanced stats if a trustworthy source exists.
Reason: FBref lost advanced stats Jan 2026; no free rich source covers South America.
Affects: data source, feature set, Álvarez case study moves to Phase 2.

## 2026-09-25: Primary data source
Decision: dcaribou/transfermarkt-datasets (snapshot 2026-07-06).
Reason: stats, bios, transfers, valuations already linked by player_id.
Affects: Stage 2 mostly handled by the dataset.

## 2026-09-25: Environment
Decision: Python 3.14.3, venv, versions pinned in requirements.txt.

## 2026-09-25: Phase 1 source leagues
Decision: BE1, NL1, PO1, TR1, SC1, DK1, GR1, RU1, UKR1.
Reason: only leagues with 2012 to 2025 stats coverage. ~2,900 rough movers to top five.
Excluded: ARG1, BRA1 and others (stats only 2024+, not enough labeled history).
Affects: Álvarez case study impossible in Phase 1; Phase 2 needs historical scraping.

## 2026-09-25: Season window
Decision: stats 2012/13 to 2025/26. Labeled transfers summer 2013 to summer 2024.
Transfers 2025+ = score only (label window not complete).

## 2026-09-25: Fees
Decision: transfer_fee not used as feature or label. Null (unknown) kept distinct from 0.

## 2026-09-25: Destination leagues
Decision: top five = GB1, ES1, IT1, L1, FR1.

## 2026-09-25: Snapshot cutoff
Decision: drop transfers dated after 2026-07-06 (snapshot date).
Reason: dataset contains future dated transfers (520 rows, max 2030-06-30).
Affects: all transfer based counts and labels.
## 2026-10-08: RAG scouting assistant added as a component
Decision: build a LangChain RAG assistant inside this repo (rag/, eval/), PostgreSQL with pgvector,
sentence transformers embeddings, Claude API default with Ollama option, 20 question SQL backed benchmark.
Reason: plain language search over pre transfer player profiles, with a measurable accuracy number.
Open: stat source (FBref advanced stats removed Jan 2026), league list vs Phase 1 sources,
DuckDB vs Postgres for the main pipeline.
Affects: new dependencies (to be pinned when step 2 starts), new Postgres setup, leakage rule applies to any RAG output fed to the model.
