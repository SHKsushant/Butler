"""
Lightweight RAG: embed the small FAQ set once, then for each ticket
retrieve the closest FAQ entry (if any) above a relevance threshold, so
the draft-reply prompt can ground itself in an actual policy answer
instead of the model guessing plausible-sounding support copy.
"""
from functools import lru_cache
import math
from typing import Optional, Tuple

from app.data.faq import FAQ_ENTRIES
from app.services.embeddings import embed_text

RELEVANCE_THRESHOLD = 0.35  # below this, treat the ticket as unmatched to any FAQ


@lru_cache(maxsize=1)
def _faq_embeddings() -> tuple:
    texts = [f"{e['question']} {e['answer']}" for e in FAQ_ENTRIES]
    return tuple(embed_text(text) for text in texts)


def _cosine_similarity(left: list, right: list) -> float:
    numerator = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    return numerator / (left_norm * right_norm) if left_norm and right_norm else 0.0


def retrieve_faq(ticket_text: str) -> Optional[Tuple[dict, float]]:
    """Returns (faq_entry, similarity_score) for the best match, or None
    if nothing clears the relevance threshold."""
    if not FAQ_ENTRIES:
        return None

    query_vec = embed_text(ticket_text)
    sims = [_cosine_similarity(query_vec, faq_vec) for faq_vec in _faq_embeddings()]
    best_idx = max(range(len(sims)), key=sims.__getitem__)
    best_score = sims[best_idx]

    if best_score < RELEVANCE_THRESHOLD:
        return None
    return FAQ_ENTRIES[best_idx], best_score
