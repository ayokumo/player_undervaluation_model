"""Embed every player season profile and every scouting note into pgvector (table rag.documents).

Needs the embedding model (EMBEDDING_MODEL, default sentence-transformers/all-MiniLM-L6-v2, 384 dimensions).
Run:  python -m rag.build_index
"""
import re
import sys
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

from rag.documents import build_profile, is_indexable
from rag.embedder import DIM, embed
from rag.store import db_url

NOTES = Path(__file__).resolve().parent.parent / "notes" / "scouting_notes"


def parse_note(path: Path) -> dict:
    raw = path.read_text()
    m = re.match(r"---\n(.*?)\n---\n(.*)", raw, re.S)
    if not m:
        raise ValueError(f"{path.name} has no front matter")
    meta = dict(line.split(": ", 1) for line in m.group(1).splitlines() if ": " in line)
    return {"doc_id": f"note_{meta['note_id']}", "title": meta["title"], "text": m.group(2).strip(), "meta": meta}


def main() -> None:
    with psycopg.connect(db_url(), autocommit=True, row_factory=dict_row) as c:
        c.execute("CREATE EXTENSION IF NOT EXISTS vector")
        c.execute("CREATE SCHEMA IF NOT EXISTS rag")
        c.execute("DROP TABLE IF EXISTS rag.documents")
        c.execute(f"""CREATE TABLE rag.documents (
            doc_id text PRIMARY KEY, doc_type text, title text, text text, name text, player_id int, season text,
            position_group text, league text, club text, age int, minutes int, market_value_eur numeric,
            embedding vector({DIM}))""")
        rows = c.execute("SELECT * FROM tm.player_season_stats").fetchall()
        docs = [build_profile(r) for r in rows if is_indexable(r)]
        print(f"embedding {len(docs):,} player season profiles", file=sys.stderr)
        for i in range(0, len(docs), 256):
            batch = docs[i:i + 256]
            vecs = embed([d.text for d in batch])
            with c.cursor() as cur:
                cur.executemany(
                    "INSERT INTO rag.documents (doc_id, doc_type, title, text, name, player_id, season, position_group, "
                    "league, club, age, minutes, market_value_eur, embedding) VALUES (%s,'stats_profile',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    [(d.doc_id, f"{d.metadata['name']} {d.metadata['season']}", d.text, d.metadata["name"], d.metadata["player_id"],
                      d.metadata["season"], d.metadata["position_group"], d.metadata["league"], d.metadata["club"],
                      d.metadata["age"], d.metadata["minutes"], d.metadata["market_value_eur"],
                      "[" + ",".join(f"{x:.6f}" for x in v) + "]") for d, v in zip(batch, vecs)])
        notes = [parse_note(p) for p in sorted(NOTES.glob("*.md")) if p.name != "README.md"]
        vecs = embed([f"{n['title']}\n{n['text']}" for n in notes])
        with c.cursor() as cur:
            for n, v in zip(notes, vecs):
                cur.execute("INSERT INTO rag.documents (doc_id, doc_type, title, text, embedding) VALUES (%s,'scouting_note',%s,%s,%s)",
                            (n["doc_id"], n["title"], n["text"], "[" + ",".join(f"{x:.6f}" for x in v) + "]"))
        c.execute("CREATE INDEX ON rag.documents USING hnsw (embedding vector_cosine_ops)")
        print(f"indexed {len(docs):,} profiles and {len(notes)} notes", file=sys.stderr)


if __name__ == "__main__":
    main()
