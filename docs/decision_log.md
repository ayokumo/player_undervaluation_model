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

## 2026-10-15: Step 2 modelling rules (fixed before counts or results were seen)
Decision: league of each club at the time of a move comes from games played (last league game on or before the date for the from club, first league game on or after for the to club), not from the club's current league.
Decision: pre transfer record needs at least 1 appearance in the 365 days before the move. Moves dated 2013-06-01 to 2024-09-30.
Decision: label regular_starter = at least 50% of possible league minutes at the new club in year 1 or year 2 after the move.
Decision: split by date with an embargo (train to 2020-06-30, validation 2022-07 to 2023-06, test from 2023-07). Models: logistic regression, gradient boosting, PyTorch MLP; baselines are the prior and a minutes rule. Hyperparameters picked on validation ROC AUC only.
Result: 1,669 records, below the resume's 3500+. Not widened to reach a target.

## 2026-10-15: Shortlist age rule (added after seeing output)
Decision: shortlist eligibility adds age 30 or under, the 95th percentile of mover ages in the training data.
Reason: the first version had no age rule and ranked 33 to 38 year old players highest, because they are cheap and the model has little signal on age at that range. This rule was set from the age distribution of real movers, not from any outcome metric.

## 2026-10-15: RAG data source and design (Step 3)
Decision: the assistant reads Transfermarkt player seasons from PostgreSQL (no scraping). 9 source leagues, seasons 2022/23 to 2025/26, 900 minutes minimum, 8,177 profiles.
Reason: FBref advanced stats are gone, StatsBomb open data covers few of these leagues, and the Transfermarkt table is already loaded and linked.
Decision: the model fills a fixed schema, code builds the SQL. The 20 benchmark questions are split 10 tune and 10 heldout before any run.
Resolved 2026-10-15: embedding model files were downloaded by the user (Hugging Face is blocked from the build environment) and the API key was supplied. Benchmark run: tune 10 of 10, held out 9 of 10.

## 2026-10-15: Computer vision component (Step 4)
Decision: use StatsBomb open event data from four national team tournaments, because the free data has no events for the nine source leagues.
Decision: players are linked to the league index by name (ratio 92 or more) AND nationality; one season per tournament.
Decision: Claude Sonnet 5.5 describes the images and picks tags from fixed lists. Rule based tags from the event data are the ground truth and thresholds were fixed before comparison.
Result: tag agreement 49% to 73% (carries worse than guessing). Vision documents did not change accuracy on the 20 league questions (19/20 both ways). On 8 vision only questions: 0/8 without, 4/8 with.
Not retuned to look better.
