"""Step 4 (planned): retrieval plus LLM chain.

Plan:
* Parse filters from the question (position, league, age, minutes) and apply them
  as pgvector metadata filters, always enforcing documents.MIN_MINUTES.
* Semantic search over the filtered set, top k records.
* LLM from .env: LLM_PROVIDER=anthropic (default) or ollama.
* Use prompts.SYSTEM_PROMPT and return the answer plus the list of cited doc_ids.
"""


def answer(question: str) -> dict:
    raise NotImplementedError("Step 4: chain not built yet")
