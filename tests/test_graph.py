"""Graph tests with a fake model, so no API key is needed. They check routing, guards and the database path."""
import re
from pathlib import Path

import psycopg
import pytest
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda

from rag.graph import build_graph, mermaid
from rag.schemas import Route, StatsQuery
from rag.store import db_url


class FakeLLM:
    def __init__(self, route="stats", query=None):
        self.route, self.query, self.answer_context = route, query or StatsQuery(), None

    def with_structured_output(self, schema):
        if schema is Route:
            return RunnableLambda(lambda _: Route(route=self.route))
        return RunnableLambda(lambda _: self.query)

    def invoke(self, messages):
        self.answer_context = messages[0].content
        return AIMessage(content="ok")


@pytest.fixture(scope="module")
def db():
    try:
        with psycopg.connect(db_url()) as c:
            c.execute("SELECT 1 FROM tm.player_season_stats LIMIT 1")
    except Exception:
        pytest.skip("database not built")


def test_unsupported_metric_abstains_without_calling_llm_to_answer(db):
    llm = FakeLLM(query=StatsQuery(unsupported_metric=True, missing_item="xG"))
    out = build_graph(llm).invoke({"question": "xG?"})
    assert out["answer"].startswith("not enough data")
    assert llm.answer_context is None


def test_unknown_season_abstains(db):
    llm = FakeLLM(query=StatsQuery(league="BE1", season="2019/20", order_by="goals"))
    out = build_graph(llm).invoke({"question": "q"})
    assert out["answer"].startswith("not enough data") and "2019/20" in out["answer"]


def test_unknown_league_abstains(db):
    out = build_graph(FakeLLM(query=StatsQuery(league="BRA1"))).invoke({"question": "q"})
    assert out["answer"].startswith("not enough data")


def test_rank_query_reaches_the_answer_with_real_records(db):
    llm = FakeLLM(query=StatsQuery(league="PO1", season="2025/26", position_group="defender", max_age=21, order_by="minutes", limit=3))
    out = build_graph(llm).invoke({"question": "q"})
    assert "Bastien Meupiyou" in llm.answer_context
    assert out["sources"][0].startswith("[Bastien Meupiyou")


def test_lookup_ignores_accents(db):
    llm = FakeLLM(query=StatsQuery(intent="lookup", player_names=["Nicolo Tresoldi"], season="2025/26"))
    build_graph(llm).invoke({"question": "q"})
    assert "Tresoldi" in llm.answer_context


def test_order_by_is_whitelisted(db):
    llm = FakeLLM(query=StatsQuery(league="BE1", season="2025/26", order_by="name; DROP TABLE x"))
    build_graph(llm).invoke({"question": "q"})
    assert "Minutes" in llm.answer_context


def test_reports_branch_without_index_abstains():
    out = build_graph(FakeLLM(route="reports"), embed_fn=None).invoke({"question": "q"})
    assert out["answer"].startswith("not enough data")


def test_readme_diagram_matches_graph():
    readme = (Path(__file__).parent.parent / "README.md").read_text()
    block = re.search(r"<!-- graph:start -->\s*```mermaid\n(.*?)```\s*<!-- graph:end -->", readme, re.S)
    assert block, "README must contain the generated graph between graph:start and graph:end"
    assert block.group(1).strip() == mermaid().strip()
