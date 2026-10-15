"""Writes draft scouting notes from the data in tm.player_season_stats (season 2025/26).

These are DATA DERIVED drafts, not eyewitness scouting. Every number comes from a query in this file, and the
text around the numbers is fixed wording. They give the reports branch of the assistant real documents to
retrieve. Replace or extend them with your own written notes: any .md file in notes/scouting_notes/ with the
same front matter is indexed.

Run:  python notes/generate_draft_notes.py
"""
import datetime
import os
from pathlib import Path

import psycopg

OUT = Path(__file__).parent / "scouting_notes"
SEASON = "2025/26"
TODAY = datetime.date.today().isoformat()
URL = os.environ.get("DATABASE_URL", "postgresql:///football")


def q(conn, sql, *args):
    return conn.execute(sql, args).fetchall()


def eur(v):
    return "n/a" if v is None else f"EUR {float(v) / 1e6:.1f}m"


def front(note_id, kind, title, leagues, player_ids):
    return (f"---\nnote_id: {note_id}\nkind: {kind}\ntitle: {title}\nauthor: draft generated from repo data\n"
            f"written: {TODAY}\nseason: {SEASON}\nleagues: [{', '.join(leagues)}]\nplayer_ids: [{', '.join(str(p) for p in player_ids)}]\n---\n")


def table(rows, header):
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    for r in rows:
        out.append("| " + " | ".join(str(x) for x in r) + " |")
    return "\n".join(out)


def main():
    OUT.mkdir(exist_ok=True)
    with psycopg.connect(URL) as c:
        # 1 Belgium
        n, age, val = q(c, "select count(*), round(avg(age),1), round(avg(market_value_eur)/1e6,2) from tm.player_season_stats where league='BE1' and season=%s", SEASON)[0]
        rows = q(c, """select name, club, age, minutes, goals, assists, goal_contrib_p90, market_value_eur, player_id from tm.player_season_stats
            where league='BE1' and season=%s and position_group in ('winger','striker','attacking_mid') order by goal_contrib_p90 desc limit 5""", SEASON)
        body = front("be1_attack_2025_26", "league_report", "Belgian Pro League attackers, 2025/26", ["BE1"], [r[8] for r in rows])
        body += f"""# Belgian Pro League attackers, {SEASON}

Draft written {TODAY} from Transfermarkt data. {n} players in the league have 900 or more minutes this season. Their average age is {age} and their average market value is EUR {val}m.

The five attacking players (wingers, strikers, attacking midfielders) with the highest goals plus assists per 90 minutes:

{table([(r[0], r[1], r[2], r[3], r[4], r[5], r[6], eur(r[7])) for r in rows], ["Player", "Club", "Age", "Minutes", "Goals", "Assists", "G+A per 90", "Market value"])}

Read this as a starting list. It only uses goals and assists, so it says nothing about chance creation or defensive work. A player on this list at an older age (check the age column) is a different recruitment case from a 20 year old with a similar rate.
"""
        (OUT / "be1_attack_2025_26.md").write_text(body)

        # 2 Netherlands
        rows = q(c, """select name, club, age, position_group, minutes, goals, assists, market_value_eur, player_id from tm.player_season_stats
            where league='NL1' and season=%s and age<=21 order by minutes desc limit 6""", SEASON)
        cnt = q(c, "select count(*) from tm.player_season_stats where league='NL1' and season=%s and age<=21 and minutes>=1500", SEASON)[0][0]
        body = front("nl1_young_core_2025_26", "league_report", "Eredivisie young regulars, 2025/26", ["NL1"], [r[8] for r in rows])
        body += f"""# Eredivisie young regulars, {SEASON}

Draft written {TODAY}. {cnt} players aged 21 or under have played 1500 or more league minutes this season. The six with the most minutes:

{table([(r[0], r[1], r[2], r[3], r[4], r[5], r[6], eur(r[7])) for r in rows], ["Player", "Club", "Age", "Position", "Minutes", "Goals", "Assists", "Market value"])}

Heavy minutes at this age mean the club trusts the player every week, which is a stronger signal than a good rate over a few games. Goals and assists understate the value of defenders and goalkeepers, so judge those positions on minutes and age first.
"""
        (OUT / "nl1_young_core_2025_26.md").write_text(body)

        # 3 Portugal defenders
        rows = q(c, """select name, club, age, minutes, yellows_p90, market_value_eur, player_id from tm.player_season_stats
            where league='PO1' and season=%s and position_group='defender' and age<=24 order by minutes desc limit 5""", SEASON)
        body = front("po1_young_defenders_2025_26", "league_report", "Liga Portugal young defenders, 2025/26", ["PO1"], [r[6] for r in rows])
        body += f"""# Liga Portugal young defenders, {SEASON}

Draft written {TODAY}. Defenders aged 24 or under with the most league minutes this season:

{table([(r[0], r[1], r[2], r[3], r[4], eur(r[5])) for r in rows], ["Player", "Club", "Age", "Minutes", "Yellow cards per 90", "Market value"])}

The data has no tackle, duel or passing numbers for defenders, so this note only supports a minutes and discipline view. A low yellow card rate with high minutes is a small positive sign and nothing more.
"""
        (OUT / "po1_young_defenders_2025_26.md").write_text(body)

        # 4 Turkey strikers
        rows = q(c, """select name, club, age, minutes, goals, goals_p90, market_value_eur, player_id from tm.player_season_stats
            where league='TR1' and season=%s and position_group='striker' order by goals_p90 desc limit 5""", SEASON)
        body = front("tr1_strikers_2025_26", "league_report", "Turkish Super Lig strikers, 2025/26", ["TR1"], [r[7] for r in rows])
        body += f"""# Turkish Super Lig strikers, {SEASON}

Draft written {TODAY}. Strikers with 900 or more minutes ranked by goals per 90:

{table([(r[0], r[1], r[2], r[3], r[4], r[5], eur(r[6])) for r in rows], ["Player", "Club", "Age", "Minutes", "Goals", "Goals per 90", "Market value"])}

The league has a high average age compared with the other eight source leagues in this project, so check ages before treating a scoring rate as a recruitment lead. Market values range widely in this list, which is why the shortlist method compares predicted success with value.
"""
        (OUT / "tr1_strikers_2025_26.md").write_text(body)

        # 5 Scotland midfield
        rows = q(c, """select name, club, age, minutes, goals, assists, assists_p90, market_value_eur, player_id from tm.player_season_stats
            where league='SC1' and season=%s and position_group in ('central_mid','attacking_mid') order by assists_p90 desc limit 5""", SEASON)
        body = front("sc1_midfield_2025_26", "league_report", "Scottish Premiership midfielders, 2025/26", ["SC1"], [r[8] for r in rows])
        body += f"""# Scottish Premiership midfielders, {SEASON}

Draft written {TODAY}. Central and attacking midfielders with 900 or more minutes ranked by assists per 90:

{table([(r[0], r[1], r[2], r[3], r[4], r[5], r[6], eur(r[7])) for r in rows], ["Player", "Club", "Age", "Minutes", "Goals", "Assists", "Assists per 90", "Market value"])}

Assists depend on teammates finishing chances, so one season is a weak signal. Players on this list with low market values are the ones to look at first if the question is about value.
"""
        (OUT / "sc1_midfield_2025_26.md").write_text(body)

        # 6 Method note
        body = front("shortlist_method", "method_report", "How the top 100 shortlist works", [], [])
        body += f"""# How the top 100 shortlist works

Draft written {TODAY}. The shortlist is produced by `python -m src.shortlist`.

1. The pre transfer models were trained on 1,669 moves from nine European leagues into the top five (see the README). The best model on validation data was a small PyTorch network.
2. For each current player in a source league the model gives a probability of becoming a regular starter within two seasons after a move, averaged over the five destination leagues.
3. The shortlist score is the percentile rank of that probability minus the percentile rank of market value inside the league. High probability and low value rank first.
4. Only players aged 30 or under with at least 450 minutes in the last 365 days are eligible.

Limits: on the test moves the models only modestly beat a simple rule based on minutes played, and market value is Transfermarkt's own estimate. The shortlist is a place to start a conversation, not a verdict that a player is undervalued.
"""
        (OUT / "shortlist_method.md").write_text(body)

        # 7 Greece age note
        rows = q(c, "select league, round(avg(age),1) from tm.player_season_stats where season=%s group by 1 order by 2 desc", SEASON)
        body = front("league_age_profile_2025_26", "league_report", "Average player age by source league, 2025/26", [r[0] for r in rows], [])
        body += f"""# Average player age by source league, {SEASON}

Draft written {TODAY}. Average age of players with 900 or more league minutes, oldest league first:

{table(rows, ["League", "Average age"])}

Age is one input to resale value and to how much a player can still develop. This is a table of averages and does not describe any single club.
"""
        (OUT / "league_age_profile_2025_26.md").write_text(body)
    print("wrote", len(list(OUT.glob("*.md"))) - 1, "notes")


if __name__ == "__main__":
    main()
