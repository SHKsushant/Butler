"""
For each ticket: decide what action it needs, and draft a ready-to-send
reply. Uses the larger model (see llm_client.DRAFT_MODEL) since this is
the output a human actually reads and sends - and grounds the reply in
a retrieved FAQ entry when one is relevant, rather than letting the
model invent policy details.
"""
from app.models import Ticket
from app.services.llm_client import complete_json, DRAFT_MODEL
from app.services.faq_retrieval import retrieve_faq

SYSTEM_PROMPT = """You are drafting a support agent's reply to a customer \
ticket. A human will review and can edit this before it is sent, so aim \
for a complete, ready-to-send draft rather than a rough outline.

Return ONLY a JSON object, no prose, no markdown fence, matching exactly:

{"action_type": "refund" | "escalate" | "answer_faq" | "forward_to_team" | \
"no_action_needed",
 "draft_reply": "<the full reply text, addressed to the customer by name \
if given, professional and warm, acknowledging the specific issue>"}

Rules:
- If relevant company policy/FAQ context is provided, ground the reply in \
it and do not contradict it.
- If the ticket is pure praise or needs no action, still write a brief \
thank-you reply and set action_type to "no_action_needed".
- Keep the reply concise: 3-6 sentences.
- Never invent specific dates, refund amounts, or policy details that \
were not given to you."""

DEFAULT_RESULT = {
    "action_type": "escalate",
    "draft_reply": (
        "Thanks for reaching out - we've received your message and a "
        "member of our team will follow up shortly."
    ),
}


def generate_draft(ticket: Ticket) -> dict:
    ticket_text = f"{ticket.subject}\n{ticket.body}"
    faq_match = retrieve_faq(ticket_text)

    context_block = ""
    if faq_match:
        entry, score = faq_match
        context_block = (
            f"\n\nRelevant policy/FAQ context (similarity {score:.2f}):\n"
            f"Q: {entry['question']}\nA: {entry['answer']}"
        )

    user_prompt = (
        f"Customer name: {ticket.sender_name or 'the customer'}\n"
        f"Category: {ticket.category}\n"
        f"Urgency: {ticket.urgency}/5\n"
        f"Sentiment: {ticket.sentiment}\n"
        f"Subject: {ticket.subject}\n"
        f"Body: {ticket.body}"
        f"{context_block}"
    )

    result = complete_json(SYSTEM_PROMPT, user_prompt, model=DRAFT_MODEL, max_tokens=600)
    if result is None or "draft_reply" not in result:
        result = dict(DEFAULT_RESULT)

    valid_actions = {
        "refund", "escalate", "answer_faq", "forward_to_team", "no_action_needed"
    }
    if result.get("action_type") not in valid_actions:
        result["action_type"] = "escalate"

    ticket.action_type = result["action_type"]
    ticket.draft_reply = result["draft_reply"]
    return result
