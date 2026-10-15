"""Link StatsBomb tournament players to players in the league index (tm.player_season_stats).

A link needs: the season (one per tournament, from the tournament start date, so a player is never split across two seasons), a name match of at least 92 (rapidfuzz ratio on the full accent
stripped name or nickname, so a first name alone does not match a full name) AND the same nationality.
One StatsBomb player maps to the best scoring TM row, ties to the row with most league minutes.
Output: results/vision/player_links.csv.   Run: python -m rag.vision.link_players
"""
import collections
import csv

import psycopg
from rapidfuzz import fuzz

from rag.store import db_url
from rag.vision.common import COMPETITIONS, ROOT, get_json, norm, season_of

NATION_ALIASES = {"turkiye": "turkey", "iran, islamic republic of": "iran", "korea, south": "south korea",
                  "korea republic": "south korea", "cote d'ivoire": "ivory coast", "cote divoire": "ivory coast",
                  "czech republic": "czechia", "dr congo": "congo dr", "united states": "usa"}


def nation(s):
    s = norm(s or "")
    return NATION_ALIASES.get(s, s)


def main() -> None:
    rows = []
    for c, s, name in COMPETITIONS:
        for m in get_json(f"matches/{c}/{s}.json"):
            for t in get_json(f"lineups/{m['match_id']}.json"):
                for p in t["lineup"]:
                    if p.get("positions"):
                        rows.append((name, m["match_id"], m["match_date"], t["team_name"], p["player_id"], p["player_name"],
                                     p.get("player_nickname"), (p.get("country") or {}).get("name")))
    # One season per tournament: the club season that just finished when the tournament started.
    start = {}
    for comp, mid, d, *_ in rows:
        start[comp] = min(start.get(comp, d), d)
    tour_season = {comp: season_of(d) for comp, d in start.items()}
    sb = {}
    for comp, mid, d, team, pid, pname, nick, country in rows:
        v = sb.setdefault((pid, comp, tour_season[comp]), {"names": {pname, nick} - {None}, "country": country, "team": team, "matches": set()})
        v["matches"].add((mid, d))
    with psycopg.connect(db_url()) as conn:
        tm = conn.execute("SELECT player_id, name, season, league, club, nationality, minutes, position_group FROM tm.player_season_stats").fetchall()
    by = collections.defaultdict(list)
    for r in tm:
        by[r[2]].append(r)
    links = []
    for (pid, comp, season), v in sb.items():
        best = None
        for r in by.get(season, []):
            sc = max(fuzz.ratio(norm(x), norm(r[1])) for x in v["names"])
            same_nat = nation(r[5]) == nation(v["country"]) or nation(r[5]).startswith(nation(v["country"])[:4])
            ok = sc >= 92 and same_nat
            if ok and (best is None or (sc, r[6]) > (best[0], best[1][6])):
                best = (sc, r)
        if best:
            sc, r = best
            links.append({"sb_player_id": pid, "sb_name": sorted(v["names"])[0], "competition": comp, "season": season,
                          "national_team": v["team"], "tm_player_id": r[0], "tm_name": r[1], "league": r[3], "club": r[4],
                          "position_group": r[7], "name_score": round(sc, 1), "n_matches": len(v["matches"]),
                          "match_ids": " ".join(str(m) for m, _ in sorted(v["matches"], key=lambda x: x[1]))})
    out = ROOT / "results" / "vision" / "player_links.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(links[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(sorted(links, key=lambda x: (x["competition"], x["tm_name"])))
    print(f"{len(sb)} StatsBomb player tournament entries, {len(links)} linked to the league index -> {out.relative_to(ROOT)}")
    print(collections.Counter(l["competition"] for l in links))


if __name__ == "__main__":
    main()
