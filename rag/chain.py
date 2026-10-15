"""Entry point: answer(question) runs the LangGraph graph with the real model.

Needs ANTHROPIC_API_KEY (in .env, never committed). The model name comes from ANTHROPIC_MODEL.
"""
import os
import re

from dotenv import load_dotenv

from rag.graph import build_graph

load_dotenv()
_GRAPH = None


def _graph():
    global _GRAPH
    if _GRAPH is None:
        from langchain_anthropic import ChatAnthropic
        from rag.embedder import embed
        llm = ChatAnthropic(model=os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5-5"), max_tokens=800)
        _GRAPH = build_graph(llm, embed_fn=embed)
    return _GRAPH


def answer(question: str) -> dict:
    out = _graph().invoke({"question": question})
    cited = re.findall(r"\[(?:Note: )?[^\[\]]+\]", out["answer"])
    return {"answer": out["answer"], "sources": out.get("sources", []), "cited": cited, "route": out.get("route"),
            "query": out.get("query")}
