"""The LangGraph graph: router, stats branch, reports branch, answer.

    python -m rag.graph --diagram     prints the Mermaid diagram generated from this graph (used in the README)

The language model is passed in, so tests can use a fake one and the benchmark uses the real one.
"""
import re
import sys
from typing import Callable, Optional, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

from rag import store
from rag.documents import build_profile
from rag.prompts import FILTER_PROMPT, ROUTER_PROMPT, SYSTEM_PROMPT
from rag.schemas import Route, StatsQuery

NOT_ENOUGH = "not enough data"


class State(TypedDict, total=False):
    question: str
    route: str
    query: dict
    records: list[dict]      # {"doc_id", "text", "cite"}
    abstain_reason: Optional[str]
    answer: str
    sources: list[str]


def build_graph(llm, embed_fn: Optional[Callable[[list[str]], list[list[float]]]] = None, use_vision: bool = True):
    router_llm = llm.with_structured_output(Route)
    filter_llm = llm.with_structured_output(StatsQuery)

    def router(state: State) -> State:
        out = router_llm.invoke([SystemMessage(content=ROUTER_PROMPT), HumanMessage(content=state["question"])])
        return {"route": out.route}

    def stats_branch(state: State) -> State:
        q = filter_llm.invoke([SystemMessage(content=FILTER_PROMPT), HumanMessage(content=state["question"])])
        q = q.model_dump()
        # Deterministic guards run before any query, so unsupported questions never reach the answer step.
        if q["unsupported_metric"]:
            return {"query": q, "records": [], "abstain_reason": f"the data has no {q.get('missing_item') or 'such stat'}"}
        if q["unsupported_league"] or (q["league"] and q["league"] not in store.VALID_LEAGUES):
            return {"query": q, "records": [], "abstain_reason": "that league is not in the data (nine leagues outside the top five only)"}
        if q["season"] and q["season"] not in store.VALID_SEASONS:
            return {"query": q, "records": [], "abstain_reason": f"season {q['season']} is not in the data (2022/23 to 2025/26 only)"}
        if q["position_group"] and q["position_group"] not in store.POSITIONS:
            q["position_group"] = None
        if q["intent"] in ("lookup", "compare") and q["player_names"]:
            rows = store.lookup_players(q["player_names"], q["season"], q["league"])
        else:
            if not q["season"]:
                q["season"] = store.LATEST_SEASON
            if q["order_by"] not in store.ORDER_COLUMNS:
                q["order_by"] = "minutes"
            rows = store.rank_players(q)
        records = []
        for i, r in enumerate(rows, 1):
            doc = build_profile(r)
            extra = f"\nRank {i} by {q['order_by']}: {r.get(q['order_by'])}" if q["intent"] == "rank" else ""
            records.append({"doc_id": doc.doc_id, "text": doc.text + extra, "cite": f"[{r['name']}, {r['season']}]"})
        if use_vision:
            seen = set()
            pairs = [(r["player_id"], r["season"]) for r in rows if not ((r["player_id"], r["season"]) in seen or seen.add((r["player_id"], r["season"])))]
            for v in store.vision_docs(pairs):
                records.append({"doc_id": v["doc_id"], "text": v["text"], "cite": f"[Vision: {v['name']}, {v['season']}]"})
        return {"query": q, "records": records, "abstain_reason": None if records else "no player records match"}

    def reports_branch(state: State) -> State:
        if embed_fn is None:
            return {"records": [], "abstain_reason": "the reports index is not available"}
        vec = embed_fn([state["question"]])[0]
        types = ("scouting_note", "vision_description") if use_vision else ("scouting_note",)
        hits = store.vector_search(vec, types, k=4)
        hits = [h for h in hits if float(h["similarity"]) >= 0.2]
        records = []
        for h in hits:
            if h["doc_type"] == "vision_description":
                records.append({"doc_id": h["doc_id"], "text": h["text"], "cite": f"[Vision: {h['name']}, {h['season']}]"})
            else:
                records.append({"doc_id": h["doc_id"], "text": f"Note title: {h['title']}\n{h['text']}", "cite": f"[Note: {h['title']}]"})
        return {"records": records, "abstain_reason": None if records else "no scouting note matches"}

    def answer(state: State) -> State:
        records = state.get("records") or []
        if not records:
            reason = state.get("abstain_reason") or "no matching records"
            return {"answer": f"{NOT_ENOUGH}. Missing: {reason}.", "sources": []}
        context = "\n\n".join(r["text"] for r in records)
        msg = llm.invoke([SystemMessage(content=SYSTEM_PROMPT.format(context=context)), HumanMessage(content=state["question"])])
        text = msg.content if isinstance(msg.content, str) else "".join(p.get("text", "") for p in msg.content)
        return {"answer": text.strip(), "sources": [r["cite"] for r in records]}

    g = StateGraph(State)
    g.add_node("router", router)
    g.add_node("stats_branch", stats_branch)
    g.add_node("reports_branch", reports_branch)
    g.add_node("answer", answer)
    g.add_edge(START, "router")
    g.add_conditional_edges("router", lambda s: s["route"], {"stats": "stats_branch", "reports": "reports_branch"})
    g.add_edge("stats_branch", "answer")
    g.add_edge("reports_branch", "answer")
    g.add_edge("answer", END)
    return g.compile()


def mermaid(llm=None) -> str:
    from langchain_core.runnables import RunnableLambda

    class _Stub:
        def with_structured_output(self, _):
            return RunnableLambda(lambda x: x)
    return build_graph(llm or _Stub()).get_graph().draw_mermaid()


if __name__ == "__main__":
    if "--diagram" in sys.argv:
        print(mermaid())
