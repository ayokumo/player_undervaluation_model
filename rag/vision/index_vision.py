"""Store the vision descriptions as extra documents in pgvector (doc_type 'vision_description') and load the
rule based truth table (tm.vision_truth) used by the vision questions.

Each document is the vision model's description and tags exactly as produced, with a header saying where it came
from. It is linked to the player and season, like the stats profiles.  Run: python -m rag.vision.index_vision
"""
import json

import pandas as pd
import psycopg

from rag.embedder import embed
from rag.store import db_url
from rag.vision.common import ROOT


def doc_text(r) -> str:
    return "\n".join([
        f"Player: {r['tm_name']} (id {r['tm_player_id']})",
        f"Season: {r['season']}",
        f"Source: image analysis of pass, carry and shot maps from {r['competition']} (national team matches, {r['n_matches']} matches),"
        " not league games. Vision derived, may be inaccurate.",
        f"League club that season: {r['club']} ({r['league']})",
        f"Description: {r['description']}",
        f"Tags: passing territory {r['passing_territory']}, pass direction {r['pass_direction']}, pass length {r['pass_length']}, "
        f"carrying {r['carrying']}, shooting {r['shooting']}"])


def main() -> None:
    desc = pd.DataFrame([json.loads(l) for l in (ROOT / "results/vision/descriptions.jsonl").read_text().splitlines() if l.strip()])
    summ = pd.read_csv(ROOT / "results/vision/action_summary.csv")
    df = desc.drop(columns=["model", "date"]).merge(summ, on=["tm_player_id", "season", "competition"])
    texts = [doc_text(r) for _, r in df.iterrows()]
    vecs = embed(texts)
    with psycopg.connect(db_url(), autocommit=True) as c:
        c.execute("DELETE FROM rag.documents WHERE doc_type = 'vision_description'")
        with c.cursor() as cur:
            cur.executemany(
                "INSERT INTO rag.documents (doc_id, doc_type, title, text, name, player_id, season, position_group, league, club, embedding) "
                "VALUES (%s,'vision_description',%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                [(f"vision_{r.tm_player_id}_{r.season}", f"{r.tm_name} {r.season} (vision)", t, r.tm_name, int(r.tm_player_id), r.season,
                  r.position_group, r.league, r.club, "[" + ",".join(f"{x:.6f}" for x in v) + "]")
                 for (_, r), t, v in zip(df.iterrows(), texts, vecs)])
        c.execute("DROP TABLE IF EXISTS tm.vision_truth")
        c.execute("""CREATE TABLE tm.vision_truth (tm_player_id int, tm_name text, season text, competition text,
            tag_passing_territory text, tag_pass_direction text, tag_pass_length text, tag_carrying text, tag_shooting text,
            vis_passing_territory text, vis_pass_direction text, vis_pass_length text, vis_carrying text, vis_shooting text)""")
        with c.cursor() as cur:
            cur.executemany("INSERT INTO tm.vision_truth VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                            [(int(r.tm_player_id), r.tm_name, r.season, r.competition, r.tag_passing_territory, r.tag_pass_direction,
                              r.tag_pass_length, r.tag_carrying, r.tag_shooting, r.passing_territory, r.pass_direction, r.pass_length,
                              r.carrying, r.shooting) for _, r in df.iterrows()])
    print(f"indexed {len(df)} vision documents")


if __name__ == "__main__":
    main()
