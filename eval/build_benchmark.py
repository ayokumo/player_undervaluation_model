"""Builds eval/benchmark.json. Every expected answer comes from running the saved SQL, never from hand.

The 20 questions are split before any run: 10 "tune" questions (used while tuning prompts) and 10 "heldout"
questions (never looked at while tuning, scored once on the frozen prompts).
Run:  python -m eval.build_benchmark
"""
import json
from pathlib import Path

import psycopg

from rag.store import db_url

OUT = Path(__file__).parent / "benchmark.json"
T = "tm.player_season_stats"


def rank_sql(league, season, cond, order, n):
    c = f" AND {cond}" if cond else ""
    return (f"SELECT name, season, {order} AS value FROM {T} WHERE league='{league}' AND season='{season}'{c} "
            f"AND minutes >= 900 ORDER BY {order} DESC NULLS LAST, minutes DESC, name LIMIT {n}")


NO_COLUMN = "SELECT count(*) AS n FROM information_schema.columns WHERE table_schema='tm' AND table_name='player_season_stats' AND column_name IN ({cols})"

QUESTIONS = [
    # ---- tuning set ----
    dict(id="t01", split="tune", type="single_fact", kind="value", question="How many goals did Christos Tzolis score in the Belgian Pro League in 2025/26?",
         sql=f"SELECT name, season, goals AS value FROM {T} WHERE name='Christos Tzolis' AND season='2025/26'"),
    dict(id="t02", split="tune", type="filtered_ranking", kind="ranking", question="Who were the top 3 wingers in the Eredivisie in 2024/25 by goals per 90, minimum 900 minutes?",
         sql=rank_sql("NL1", "2024/25", "position_group='winger'", "goals_p90", 3)),
    dict(id="t03", split="tune", type="filtered_ranking", kind="ranking", question="Which 3 defenders aged 21 or under had the most minutes in Liga Portugal in 2025/26?",
         sql=rank_sql("PO1", "2025/26", "position_group='defender' AND age<=21", "minutes", 3)),
    dict(id="t04", split="tune", type="comparison", kind="comparison", question="Who had the higher goals per 90 in the 2025/26 Turkish Super Lig, Victor Osimhen or Mauro Icardi?",
         sql=f"SELECT name, season, goals_p90 AS value FROM {T} WHERE league='TR1' AND season='2025/26' AND name IN ('Victor Osimhen','Mauro Icardi') ORDER BY goals_p90 DESC"),
    dict(id="t05", split="tune", type="reports", kind="value", question="According to the scouting notes, which Belgian Pro League attacker had the highest goals plus assists per 90 in 2025/26?",
         sql=rank_sql("BE1", "2025/26", "position_group IN ('winger','striker','attacking_mid')", "goal_contrib_p90", 1)),
    dict(id="t06", split="tune", type="not_enough_data", kind="ned", question="What was Christos Tzolis's xG per 90 in 2025/26?",
         sql=NO_COLUMN.format(cols="'xg','xg_p90','xa_p90'")),
    dict(id="t07", split="tune", type="not_enough_data", kind="ned", question="Who was the best striker in the Brazilian Serie A in 2024/25?",
         sql="SELECT count(*) AS n FROM tm.player_season_stats WHERE league IN ('BRA1')"),
    dict(id="t08", split="tune", type="single_fact", kind="value", question="What was Ardon Jashari's market value at the end of 2024/25?",
         sql=f"SELECT name, season, market_value_eur AS value FROM {T} WHERE name='Ardon Jashari' AND season='2024/25'"),
    dict(id="t09", split="tune", type="filtered_ranking", kind="ranking", question="Who were the top 3 central midfielders in the Scottish Premiership in 2025/26 by assists per 90, minimum 900 minutes?",
         sql=rank_sql("SC1", "2025/26", "position_group='central_mid'", "assists_p90", 3)),
    dict(id="t10", split="tune", type="not_enough_data", kind="ned", question="How many passes did Joey Veerman complete in 2025/26?",
         sql=NO_COLUMN.format(cols="'passes','passes_completed','pass_accuracy'")),
    # ---- held out set ----
    dict(id="h01", split="heldout", type="single_fact", kind="value", question="How many minutes did Frederik Tingager play in the Danish Superliga in 2023/24?",
         sql=f"SELECT name, season, minutes AS value FROM {T} WHERE name='Frederik Tingager' AND season='2023/24'"),
    dict(id="h02", split="heldout", type="filtered_ranking", kind="ranking", question="Name the top 3 strikers in the Greek Super League in 2024/25 by goals per 90, minimum 900 minutes.",
         sql=rank_sql("GR1", "2024/25", "position_group='striker'", "goals_p90", 3)),
    dict(id="h03", split="heldout", type="filtered_ranking", kind="ranking", question="Which 3 goalkeepers played the most minutes in the Ukrainian Premier League in 2024/25?",
         sql=rank_sql("UKR1", "2024/25", "position_group='goalkeeper'", "minutes", 3)),
    dict(id="h04", split="heldout", type="comparison", kind="comparison", question="Who provided more assists in the 2025/26 Eredivisie, Joey Veerman or Ivan Perišić?",
         sql=f"SELECT name, season, assists AS value FROM {T} WHERE league='NL1' AND season='2025/26' AND name IN ('Joey Veerman','Ivan Perišić') ORDER BY assists DESC"),
    dict(id="h05", split="heldout", type="reports", kind="value", question="According to the scouting notes, which of the nine leagues had the oldest average player age in 2025/26?",
         sql=f"SELECT league_name AS name, season, round(avg(age),1) AS value FROM {T} WHERE season='2025/26' GROUP BY league_name, season ORDER BY avg(age) DESC LIMIT 1"),
    dict(id="h06", split="heldout", type="filtered_ranking", kind="ranking", question="Which 2 players aged 21 or under scored the most goals in the Russian Premier League in 2025/26?",
         sql=rank_sql("RU1", "2025/26", "age<=21", "goals", 2)),
    dict(id="h07", split="heldout", type="not_enough_data", kind="ned", question="Which Danish Superliga player had the best pressing numbers in 2025/26?",
         sql=NO_COLUMN.format(cols="'pressures','pressing','tackles_p90'")),
    dict(id="h08", split="heldout", type="not_enough_data", kind="ned", question="Who scored the most goals in the Belgian Pro League in 2019/20?",
         sql=f"SELECT count(*) AS n FROM {T} WHERE season='2019/20'"),
    dict(id="h09", split="heldout", type="single_fact", kind="value", question="Which club did Rafa Silva play for in Liga Portugal in 2023/24?",
         sql=f"SELECT name, season, club AS value FROM {T} WHERE name='Rafa Silva' AND season='2023/24' AND league='PO1'"),
    dict(id="h10", split="heldout", type="filtered_ranking", kind="ranking", question="Who were the top 3 attacking midfielders aged 22 or under in the Eredivisie in 2025/26 by goals plus assists per 90, minimum 900 minutes?",
         sql=rank_sql("NL1", "2025/26", "position_group='attacking_mid' AND age<=22", "goal_contrib_p90", 3)),
]


def vision_questions(conn) -> list[dict]:
    """8 extra questions answerable only from the vision derived documents. The players are picked at random
    (seed 7) from tm.vision_truth before any assistant run, one attribute per question."""
    import random
    rng = random.Random(7)
    spec = [  # (tag column, question template, {tag: option text}, options in question)
        ("tag_passing_territory", "In the {comp} pass maps for {name}, did his passes mostly start in his own half, in the final third, or was it balanced? Answer with one of: own half, final third, balanced.",
         {"mostly_own_half": "own half", "mostly_final_third": "final third", "balanced": "balanced"}),
        ("tag_passing_territory", "In the {comp} pass maps for {name}, did his passes mostly start in his own half, in the final third, or was it balanced? Answer with one of: own half, final third, balanced.",
         {"mostly_own_half": "own half", "mostly_final_third": "final third", "balanced": "balanced"}),
        ("tag_pass_direction", "In the {comp} pass maps for {name}, were his passes mostly forward, mostly sideways or back, or mixed? Answer with one of: forward, sideways or back, mixed.",
         {"mostly_forward": "forward", "mostly_sideways_or_back": "sideways or back", "mixed": "mixed"}),
        ("tag_pass_direction", "In the {comp} pass maps for {name}, were his passes mostly forward, mostly sideways or back, or mixed? Answer with one of: forward, sideways or back, mixed.",
         {"mostly_forward": "forward", "mostly_sideways_or_back": "sideways or back", "mixed": "mixed"}),
        ("tag_pass_length", "In the {comp} pass maps for {name}, was his passing short, medium or long? Answer with one of: short, medium, long.",
         {"short": "short", "medium": "medium", "long": "long"}),
        ("tag_pass_length", "In the {comp} pass maps for {name}, was his passing short, medium or long? Answer with one of: short, medium, long.",
         {"short": "short", "medium": "medium", "long": "long"}),
        ("tag_shooting", "In the {comp} shot maps for {name}, were his shots mostly from close range, from long range, or mixed? Answer with one of: close, long range, mixed.",
         {"shots_from_close": "close", "shots_from_range": "long range", "shots_mixed": "mixed"}),
        ("tag_carrying", "In the {comp} carry maps for {name}, did he make several carries into the final third? Answer with one of: yes, no.",
         {"carries_into_final_third": "yes", "few_carries_into_final_third": "no"}),
    ]
    used, out = set(), []
    for i, (col, tmpl, mapping) in enumerate(spec, 1):
        rows = conn.execute(f"SELECT tm_player_id, tm_name, season, competition, {col} FROM tm.vision_truth WHERE {col} = ANY(%s) ORDER BY tm_player_id", [list(mapping)]).fetchall()
        rows = [r for r in rows if r[0] not in used]
        pid, name, season, comp, tag = rng.choice(rows)
        used.add(pid)
        out.append(dict(id=f"v{i:02d}", split="vision", type="vision", kind="choice", question=tmpl.format(comp=comp, name=name),
                        sql=f"SELECT tm_name AS name, season, {col} AS value FROM tm.vision_truth WHERE tm_player_id = {pid} AND competition = '{comp}'",
                        options=list(mapping.values())))
    return out


def main() -> None:
    out = []
    with psycopg.connect(db_url()) as c:
        has_vision = c.execute("SELECT to_regclass('tm.vision_truth')").fetchone()[0] is not None
        for q in QUESTIONS + (vision_questions(c) if has_vision else []):
            cur = c.execute(q["sql"])
            cols = [d.name for d in cur.description]
            rows = [dict(zip(cols, [float(v) if hasattr(v, "as_tuple") else v for v in r])) for r in cur.fetchall()]
            q = dict(q, expected_rows=rows, scored=True)
            if q["kind"] == "choice":
                tag = rows[0]["value"]
                col_map = {"tag_passing_territory": {"mostly_own_half": "own half", "mostly_final_third": "final third", "balanced": "balanced"},
                           "tag_pass_direction": {"mostly_forward": "forward", "mostly_sideways_or_back": "sideways or back", "mixed": "mixed"},
                           "tag_pass_length": {"short": "short", "medium": "medium", "long": "long"},
                           "tag_shooting": {"shots_from_close": "close", "shots_from_range": "long range", "shots_mixed": "mixed"},
                           "tag_carrying": {"carries_into_final_third": "yes", "few_carries_into_final_third": "no"}}
                col = q["sql"].split("AS value")[0].split(",")[-1].strip()
                q["expected_option"] = col_map[col][tag]
            if q["kind"] == "ned":
                assert rows[0]["n"] == 0, f"{q['id']}: expected an empty result but got {rows}"
            out.append(q)
    OUT.write_text(json.dumps({
        "version": 3,
        "rules": ["split vision = 8 extra questions answerable only from the vision derived documents, expected answers come from the rule based tags computed from StatsBomb events (tm.vision_truth).","Every expected answer comes from running the saved SQL against tm.player_season_stats.",
                  "split tune = questions used while tuning prompts. split heldout = never used while tuning, scored once on frozen prompts.",
                  "not_enough_data questions: the saved SQL returns 0 (the stat, league or season is not in the data)."],
        "questions": out}, indent=2, ensure_ascii=False))
    print(f"wrote {len(out)} questions ({sum(q['split']=='tune' for q in out)} tune, {sum(q['split']=='heldout' for q in out)} heldout, {sum(q['split']=='vision' for q in out)} vision)")


if __name__ == "__main__":
    main()
