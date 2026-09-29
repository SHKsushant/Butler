"""
Embedding generation for dedup/clustering. Loaded once as a module-level
singleton since loading the model is the expensive part - reused across
every ticket in a batch.
"""
from functools import lru_cache
from typing import Any, List
import hashlib
import os
import re

MODEL_NAME = "all-MiniLM-L6-v2"  # small, fast, good enough for short text


@lru_cache(maxsize=1)
def get_model() -> Any:
    # Import lazily so the app works out of the box without PyTorch or a
    # network model download. Set USE_SEMANTIC_EMBEDDINGS=true after installing
    # requirements-ml.txt to use the stronger model in production.
    if os.getenv("USE_SEMANTIC_EMBEDDINGS", "").lower() not in {"1", "true", "yes"}:
        raise RuntimeError("Semantic embeddings are disabled")
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(MODEL_NAME)


def embed_text(text: str) -> List[float]:
    try:
        model = get_model()
        vec = model.encode(text, normalize_embeddings=True)
        return vec.tolist()
    except Exception:
        # Keeps the product demonstrable when Hugging Face is unavailable.
        # This is deliberately a deterministic lexical fallback, not a
        # replacement for the semantic model used in normal operation.
        vector = [0.0] * 256
        for token in re.findall(r"[a-z0-9]+", text.lower()):
            index = int(hashlib.sha256(token.encode("utf-8")).hexdigest(), 16) % len(vector)
            vector[index] += 1.0
        magnitude = sum(value * value for value in vector) ** 0.5
        return [value / magnitude for value in vector] if magnitude else vector


def embed_ticket_text(subject: str, body: str) -> List[float]:
    # Subject carries a lot of signal for short tickets - weight it in by
    # repeating it once rather than diluting it inside a long body.
    combined = f"{subject}\n{subject}\n{body}"
    return embed_text(combined)
