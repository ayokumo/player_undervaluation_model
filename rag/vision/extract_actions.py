"""Extract passes, carries and shots of the linked players from StatsBomb event files.

Output: data/interim/sb_actions.csv (gitignored). Run: python -m rag.vision.extract_actions
"""
import csv
from concurrent.futures import ThreadPoolExecutor

from rag.vision.common import INTERIM, ROOT, get_json

FIELDS = ["sb_player_id", "match_id", "type", "x", "y", "end_x", "end_y", "outcome", "xg", "length", "minute", "is_goal"]


def actions_for(match_id: int, wanted: set[int]) -> list[list]:
    rows = []
    for e in get_json(f"events/{match_id}.json"):
        t, p = e["type"]["name"], e.get("player")
        if t not in ("Pass", "Carry", "Shot") or not p or p["id"] not in wanted or "location" not in e:
            continue
        x, y = e["location"][:2]
        if t == "Pass":
            d = e["pass"]
            end, outcome, xg, length, goal = d["end_location"], d.get("outcome", {}).get("name", "Complete"), None, d.get("length"), 0
        elif t == "Carry":
            end, outcome, xg, length, goal = e["carry"]["end_location"], "Carry", None, None, 0
        else:
            d = e["shot"]
            end, outcome, xg, length, goal = d["end_location"][:2], d["outcome"]["name"], d.get("statsbomb_xg"), None, int(d["outcome"]["name"] == "Goal")
        rows.append([p["id"], match_id, t, x, y, end[0], end[1], outcome, xg, length, e["minute"], goal])
    return rows


def main() -> None:
    links = list(csv.DictReader(open(ROOT / "results" / "vision" / "player_links.csv")))
    wanted: dict[int, set[int]] = {}
    for l in links:
        for m in l["match_ids"].split():
            wanted.setdefault(int(m), set()).add(int(l["sb_player_id"]))
    INTERIM.mkdir(parents=True, exist_ok=True)
    out = INTERIM / "sb_actions.csv"
    n = 0
    with out.open("w", newline="") as f, ThreadPoolExecutor(8) as ex:
        w = csv.writer(f)
        w.writerow(FIELDS)
        for rows in ex.map(lambda m: actions_for(m, wanted[m]), sorted(wanted)):
            w.writerows(rows)
            n += len(rows)
    print(f"{len(wanted)} matches, {n:,} actions -> {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
