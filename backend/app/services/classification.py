"""
Classification: for each ticket, get category, urgency (1-5), and
sentiment. This is the one call every downstream step depends on, so
its failure mode matters - a ticket that fails classification still
gets a safe default rather than disappearing from the queue.
"""
from app.models import Ticket
from app.services.llm_client import complete_json, CLASSIFY_MODEL

SYSTEM_PROMPT = """You triage customer support tickets. Given a ticket's \
subject and body, classify it and return ONLY a JSON object, no prose, \
no markdown fence, matching exactly this shape:

{"category": "billing" | "bug" | "complaint" | "feature_request" | \
"account_access" | "question" | "praise" | "other",
 "urgency": <integer 1-5, 5 = needs action within the hour>,
 "sentiment": "positive" | "neutral" | "negative",
 "sentiment_score": <float from -1.0 (very negative) to 1.0 (very positive)>,
 "confidence": <float from 0.0 to 1.0 - your own confidence in this \
classification. Use a LOWER number when the ticket is ambiguous, sarcastic, \
mixes multiple issues, or has too little content to be sure. Use a HIGH \
number only when the category, urgency, and sentiment are all clearly \
supported by the text.>}

Judge urgency from the content itself - explicit deadlines, blockers, \
account lockouts, or money-related failures are more urgent than \
general questions or feature requests. Be honest about confidence - it's \
used to decide which tickets a human double-checks, so it's not helpful \
to always claim certainty."""

DEFAULT_RESULT = {
    "category": "other",
    "urgency": 3,
    "sentiment": "neutral",
    "sentiment_score": 0.0,
    "confidence": 0.0,  # a fallback result should never look confident
}

# Below this, the ticket gets flagged for a human to double-check the
# AI's tagging rather than trusting it silently.
REVIEW_CONFIDENCE_THRESHOLD = 0.55


def classify_ticket(ticket: Ticket) -> dict:
    """Returns the classification dict and also mutates `ticket` in place."""
    user_prompt = f"Subject: {ticket.subject}\n\nBody: {ticket.body}"

    result = complete_json(SYSTEM_PROMPT, user_prompt, model=CLASSIFY_MODEL)
    if result is None:
        result = dict(DEFAULT_RESULT)

    # Defensive clamping in case the model drifts outside the contract
    result["urgency"] = max(1, min(5, int(result.get("urgency", 3))))
    result["sentiment_score"] = max(
        -1.0, min(1.0, float(result.get("sentiment_score", 0.0)))
    )
    result["confidence"] = max(0.0, min(1.0, float(result.get("confidence", 0.5))))
    if result.get("category") not in {
        "billing", "bug", "complaint", "feature_request",
        "account_access", "question", "praise", "other",
    }:
        result["category"] = "other"
    if result.get("sentiment") not in {"positive", "neutral", "negative"}:
        result["sentiment"] = "neutral"

    ticket.category = result["category"]
    ticket.urgency = result["urgency"]
    ticket.sentiment = result["sentiment"]
    ticket.sentiment_score = result["sentiment_score"]
    ticket.confidence = result["confidence"]
    ticket.needs_review = result["confidence"] < REVIEW_CONFIDENCE_THRESHOLD
    return result
