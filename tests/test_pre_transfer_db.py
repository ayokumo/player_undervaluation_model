"""Checks on the PostgreSQL pre transfer table. Skipped when the database has not been built."""
import psycopg
import pytest

from src.modeling import db_url


@pytest.fixture(scope="module")
def conn():
    try:
        c = psycopg.connect(db_url())
        c.execute("SELECT 1 FROM tm.model_records LIMIT 1")
    except Exception:
        pytest.skip("tm.model_records not built; run src.load_postgres and sql/01_build_pre_transfer.sql")
    yield c
    c.close()


def one(conn, sql):
    return conn.execute(sql).fetchone()[0]


def test_no_duplicate_moves(conn):
    assert one(conn, "SELECT count(*) - count(DISTINCT (player_id, transfer_date, to_club_id)) FROM tm.model_records") == 0


def test_only_source_to_top5(conn):
    bad = one(conn, """SELECT count(*) FROM tm.model_records WHERE
        from_league NOT IN ('BE1','NL1','PO1','TR1','SC1','DK1','GR1','RU1','UKR1')
        OR to_league NOT IN ('GB1','ES1','IT1','L1','FR1')""")
    assert bad == 0


def test_dates_inside_label_window(conn):
    assert one(conn, "SELECT count(*) FROM tm.model_records WHERE transfer_date > DATE '2024-09-30' OR transfer_date < DATE '2013-06-01'") == 0


def test_features_use_only_prior_appearances(conn):
    """Recompute minutes in the 365 days before the move straight from raw appearances and compare."""
    mism = one(conn, """SELECT count(*) FROM (
        SELECT r.move_id, r.minutes_365,
          (SELECT coalesce(sum(nullif(a.minutes_played,'')::int),0) FROM tm_raw.appearances a
            WHERE a.player_id::int = r.player_id AND a.date::date < r.transfer_date AND a.date::date >= r.transfer_date - 365) AS check_min
        FROM tm.model_records r ORDER BY r.move_id LIMIT 200) t WHERE t.minutes_365 <> t.check_min""")
    assert mism == 0


def test_label_matches_rule(conn):
    bad = one(conn, """SELECT count(*) FROM tm.model_records WHERE regular_starter <>
        CASE WHEN (den_y1 > 0 AND minutes_y1 >= 0.5 * den_y1) OR (den_y2 > 0 AND minutes_y2 >= 0.5 * den_y2) THEN 1 ELSE 0 END""")
    assert bad == 0


def test_every_record_has_a_prior_appearance(conn):
    assert one(conn, "SELECT count(*) FROM tm.model_records WHERE apps_365 < 1 OR apps_365 IS NULL") == 0
