"""Sentence transformers embeddings, run locally. EMBEDDING_MODEL can be a hub name or a local folder."""
import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()

DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DIM = 384


@lru_cache(maxsize=1)
def _model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(os.environ.get("EMBEDDING_MODEL", DEFAULT_MODEL))


def embed(texts: list[str]) -> list[list[float]]:
    return _model().encode(texts, normalize_embeddings=True, show_progress_bar=False).tolist()
