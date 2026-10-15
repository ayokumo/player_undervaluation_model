"""Numbers and rule based tags per linked player from the StatsBomb actions. These are the ground truth the vision
descriptions are checked against.  Tags use fixed thresholds on the 120 x 80 StatsBomb pitch (yards).

Run: python -m rag.vision.summarise   -> results/vision/action_summary.csv
"""
import csv
import math

import pandas as pd

from rag.vision.common import INTERIM, ROOT

MIN_PASSES, MIN_SHOTS = 40, 3     # a player needs one of these to get an image


def tag_row(a: pd.DataFrame, n_matches: int) -> dict:
    p, c, s = a[a.type == "Pass"], a[a.type == "Carry"], a[a.type == "Shot"]
    out = {"passes": len(p), "carries": len(c), "shots": len(s)}
    if len(p):
        dx = p.end_x - p.x
        out["pass_completion"] = round(float((p.outcome == "Complete").mean()), 3)
        out["pass_start_final_third"] = round(float((p.x >= 80).mean()), 3)
        out["pass_start_own_half"] = round(float((p.x < 60).mean()), 3)
        out["pass_forward"] = round(float((dx > 5).mean()), 3)
        out["pass_backward"] = round(float((dx < -5).mean()), 3)
        out["avg_pass_length"] = round(float(p.length.mean()), 1)
        out["tag_passing_territory"] = ("mostly_own_half" if out["pass_start_own_half"] >= 0.6
                                        else "mostly_final_third" if out["pass_start_final_third"] >= 0.4 else "balanced")
        out["tag_pass_direction"] = ("mostly_forward" if out["pass_forward"] >= 0.5
                                     else "mostly_sideways_or_back" if out["pass_forward"] < 0.3 else "mixed")
        out["tag_pass_length"] = ("long" if out["avg_pass_length"] >= 25 else "short" if out["avg_pass_length"] <= 17 else "medium")
    cf = c[(c.end_x >= 80) & (c.x < 80)]
    out["carries_into_final_third"] = len(cf)
    out["carries_into_final_third_per_match"] = round(len(cf) / max(n_matches, 1), 2)
    out["tag_carrying"] = "carries_into_final_third" if len(cf) / max(n_matches, 1) >= 2 else "few_carries_into_final_third"
    out["xg_total"] = round(float(s.xg.sum()), 2) if len(s) else 0.0
    out["goals"] = int(s.is_goal.sum()) if len(s) else 0
    if len(s) >= 2:
        d = ((120 - s.x) ** 2 + (40 - s.y) ** 2).pow(0.5)
        out["avg_shot_distance"] = round(float(d.mean()), 1)
        out["tag_shooting"] = "shots_from_close" if d.mean() <= 16 else "shots_from_range" if d.mean() >= 22 else "shots_mixed"
    else:
        out["tag_shooting"] = "too_few_shots"
    return out


def main() -> None:
    acts = pd.read_csv(INTERIM / "sb_actions.csv")
    links = list(csv.DictReader(open(ROOT / "results" / "vision" / "player_links.csv")))
    rows = []
    for l in links:
        ids = {int(m) for m in l["match_ids"].split()}
        a = acts[(acts.sb_player_id == int(l["sb_player_id"])) & acts.match_id.isin(ids)]
        t = tag_row(a, int(l["n_matches"]))
        t["eligible_for_image"] = t["passes"] >= MIN_PASSES or t["shots"] >= MIN_SHOTS
        rows.append({**{k: l[k] for k in ("tm_player_id", "tm_name", "season", "competition", "league", "club", "position_group", "n_matches", "sb_player_id", "national_team")}, **t})
    df = pd.DataFrame(rows)
    df.to_csv(ROOT / "results" / "vision" / "action_summary.csv", index=False)
    print(len(df), "linked,", int(df.eligible_for_image.sum()), "eligible for an image")
    for c in ["tag_passing_territory", "tag_pass_direction", "tag_pass_length", "tag_carrying", "tag_shooting"]:
        print(c, df[df.eligible_for_image][c].value_counts().to_dict())


if __name__ == "__main__":
    main()
