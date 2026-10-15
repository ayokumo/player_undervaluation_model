"""Step 3 ingest: build the player season table the assistant reads, and log where it came from.

Source decision (docs/decision_log.md, 2026-10-15): the assistant reads the Transfermarkt snapshot already
loaded into PostgreSQL (appearances, goals, assists, cards, minutes, market value). FBref advanced stats were
removed in January 2026, so there is no xG or progressive passing to ingest. Nothing is scraped.

Run (after src.load_postgres and sql/01):  python -m rag.ingest
"""
import sys
from datetime import date
from pathlib import Path

import psycopg

from rag.store import db_url

SQL = Path(__file__).resolve().parent.parent / "sql" / "03_player_seasons.sql"


def main() -> None:
    with psycopg.connect(db_url(), autocommit=True) as c:
        c.execute(SQL.read_text())
        n = c.execute("SELECT count(*) FROM tm.player_season_stats").fetchone()[0]
        c.execute("CREATE SCHEMA IF NOT EXISTS rag")
        c.execute("""CREATE TABLE IF NOT EXISTS rag.provenance (
            loaded_on date, source text, snapshot text, table_name text, row_count bigint)""")
        c.execute("INSERT INTO rag.provenance VALUES (%s, %s, %s, %s, %s)",
                  (date.today(), "dcaribou transfermarkt-datasets", "2026-07-06", "tm.player_season_stats", n))
    print(f"tm.player_season_stats: {n:,} player seasons", file=sys.stderr)


if __name__ == "__main__":
    main()
