"""Database access for the assistant: whitelisted stats queries and pgvector search.

The language model never writes SQL. It fills a StatsQuery (rag/schemas.py) and this module turns it into a
parameterised query. Column names that appear in SQL come from fixed whitelists below, never from user text.
"""
import os

import psycopg
from psycopg.rows import dict_row

VALID_LEAGUES = {"BE1", "NL1", "PO1", "TR1", "SC1", "DK1", "GR1", "RU1", "UKR1"}
VALID_SEASONS = {"2022/23", "2023/24", "2024/25", "2025/26"}
LATEST_SEASON = "2025/26"
POSITIONS = {"winger", "striker", "attacking_mid", "central_mid", "defender", "goalkeeper"}
ORDER_COLUMNS = {"goals", "assists", "goals_p90", "assists_p90", "goal_contrib_p90", "yellows_p90", "minutes",
                 "minutes_per_app", "market_value_eur", "age", "apps"}
SELECT_COLUMNS = ("player_id, name, season, position_group, league, league_name, club, age, apps, minutes, goals, "
                  "assists, yellows, reds, goals_p90, assists_p90, goal_contrib_p90, yellows_p90, minutes_per_app, "
                  "market_value_eur")


def db_url() -> str:
    return os.environ.get("DATABASE_URL", "postgresql:///football")


def connect():
    return psycopg.connect(db_url(), row_factory=dict_row)


def rank_players(q: dict, limit: int | None = None) -> list[dict]:
    """Top N players for a rank intent. q holds league, season, position_group, min_age, max_age, order_by, limit."""
    where, args = ["minutes >= 900"], []
    for col, key in (("league", "league"), ("season", "season"), ("position_group", "position_group")):
        if q.get(key):
            where.append(f"{col} = %s")
            args.append(q[key])
    if q.get("min_age") is not None:
        where.append("age >= %s")
        args.append(q["min_age"])
    if q.get("max_age") is not None:
        where.append("age <= %s")
        args.append(q["max_age"])
    order = q.get("order_by") or "minutes"
    if order not in ORDER_COLUMNS:
        raise ValueError(f"order_by not allowed: {order}")
    n = min(int(limit or q.get("limit") or 5), 10)
    sql = (f"SELECT {SELECT_COLUMNS} FROM tm.player_season_stats WHERE {' AND '.join(where)} "
           f"ORDER BY {order} DESC NULLS LAST, minutes DESC, name LIMIT {n}")
    with connect() as c:
        return c.execute(sql, args).fetchall()


def lookup_players(names: list[str], season: str | None = None, league: str | None = None) -> list[dict]:
    """Records for named players (accent and case insensitive), optionally for one season or league."""
    rows: list[dict] = []
    with connect() as c:
        for name in names[:4]:
            where, args = ["unaccent(lower(name)) = unaccent(lower(%s))"], [name.strip()]
            if season:
                where.append("season = %s")
                args.append(season)
            if league:
                where.append("league = %s")
                args.append(league)
            found = c.execute(f"SELECT {SELECT_COLUMNS} FROM tm.player_season_stats WHERE {' AND '.join(where)} "
                              "ORDER BY season DESC, minutes DESC LIMIT 8", args).fetchall()
            if not found:   # fall back to a contains match
                where[0] = "unaccent(lower(name)) LIKE '%%' || unaccent(lower(%s)) || '%%'"
                found = c.execute(f"SELECT {SELECT_COLUMNS} FROM tm.player_season_stats WHERE {' AND '.join(where)} "
                                  "ORDER BY season DESC, minutes DESC LIMIT 8", args).fetchall()
            rows.extend(found)
    return rows


def vector_search(embedding: list[float], doc_type: str | tuple, k: int = 3, filters: dict | None = None) -> list[dict]:
    """Nearest documents by cosine distance, with optional metadata filters. doc_type may be one type or a tuple."""
    types = [doc_type] if isinstance(doc_type, str) else list(doc_type)
    where, args = ["doc_type = ANY(%s)"], [types]
    for key in ("league", "season", "position_group"):
        if filters and filters.get(key):
            where.append(f"{key} = %s")
            args.append(filters[key])
    if filters and filters.get("max_age") is not None:
        where.append("age <= %s")
        args.append(filters["max_age"])
    vec = "[" + ",".join(f"{x:.6f}" for x in embedding) + "]"
    sql = (f"SELECT doc_id, doc_type, title, text, name, season, 1 - (embedding <=> %s::vector) AS similarity "
           f"FROM rag.documents WHERE {' AND '.join(where)} ORDER BY embedding <=> %s::vector LIMIT {int(k)}")
    with connect() as c:
        return c.execute(sql, [vec, *args, vec]).fetchall()


def vision_docs(pairs: list[tuple[int, str]]) -> list[dict]:
    """Vision derived documents for (player_id, season) pairs, if they exist."""
    if not pairs:
        return []
    out = []
    with connect() as c:
        for pid, season in pairs:
            out += c.execute("SELECT doc_id, name, season, text FROM rag.documents WHERE doc_type = 'vision_description' "
                             "AND player_id = %s AND season = %s", [pid, season]).fetchall()
    return out
