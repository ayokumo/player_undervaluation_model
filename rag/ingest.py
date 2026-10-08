"""Step 2 (planned): pull player season stats for leagues outside the top five into Postgres.

Plan:
* Check live what soccerdata (FBref) still returns per league and season, since
  FBref advanced stats were removed in Jan 2026. Add StatsBomb open data where it covers a target league.
* Cache every response locally under data/raw/rag/ (gitignored), rate limit requests,
  respect each source's terms and robots rules.
* Write raw rows untouched to a Postgres table (raw_player_season_stats) and log
  source, date pulled and row count to a provenance table.
"""


def main() -> None:
    raise NotImplementedError("Step 2: data pull not built yet")


if __name__ == "__main__":
    main()
