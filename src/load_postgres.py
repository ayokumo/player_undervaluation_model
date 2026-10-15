"""Load the Transfermarkt snapshot into PostgreSQL as raw text tables (schema tm_raw).

Everything is loaded as text on purpose. Typing and cleaning happen in sql/01_build_pre_transfer.sql
so the raw load never silently drops or coerces a value.

Run:  python -m src.load_postgres
Needs DATABASE_URL (see .env.example). Default: postgresql:///football
"""
import csv
import os
import sys

import psycopg

from src.config import RAW_DIR

TABLES = ["players", "transfers", "clubs", "competitions", "games", "appearances", "player_valuations"]


def main() -> None:
    url = os.environ.get("DATABASE_URL", "postgresql:///football")
    with psycopg.connect(url, autocommit=True) as conn:
        conn.execute("CREATE SCHEMA IF NOT EXISTS tm_raw")
        for t in TABLES:
            path = RAW_DIR / f"{t}.csv"
            with open(path, newline="", encoding="utf-8") as f:
                header = next(csv.reader(f))
            cols = ", ".join(f'"{c}" text' for c in header)
            conn.execute(f"DROP TABLE IF EXISTS tm_raw.{t}")
            conn.execute(f"CREATE TABLE tm_raw.{t} ({cols})")
            with open(path, "rb") as f, conn.cursor() as cur:
                with cur.copy(f"COPY tm_raw.{t} FROM STDIN WITH (FORMAT csv, HEADER true)") as cp:
                    while chunk := f.read(1 << 20):
                        cp.write(chunk)
            n = conn.execute(f"SELECT count(*) FROM tm_raw.{t}").fetchone()[0]
            print(f"tm_raw.{t}: {n:,} rows", file=sys.stderr)


if __name__ == "__main__":
    main()
