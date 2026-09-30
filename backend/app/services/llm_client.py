"""
Thin wrapper around the Groq API - chosen specifically because it has a
genuinely free, no-credit-card developer tier (unlike most commercial
LLM APIs), which matters for a hackathon team that doesn't want to put
a card on file. Get a free key at https://console.groq.com/keys.

Two models are used deliberately, not arbitrarily:
- An 8B "instant" model for classification: this runs once per ticket
  and needs to be fast, not deep - a short label set doesn't need a
  70B model.
- A 70B model for draft replies: this is the part a human actually
  reads and sends, so it's worth spending more capability on tone and
  grounding.

Every call asks for JSON only (and requests Groq's native JSON mode
where supported) and is defended with a retry + a safe fallback,
because a single malformed response should never take down the whole
pipeline for the other 99 tickets.
"""
import json
import os
import re
import time
from typing import Optional

from groq import Groq
from dotenv import load_dotenv

_client: Optional[Groq] = None
last_error: Optional[str] = None  # most recent LLM failure, shown by /llm-check

# Load backend/.env when the app is started locally.  Deployment platforms
# provide environment variables directly, which dotenv leaves untouched.
load_dotenv()

# Groq retired llama-3.1-8b-instant and llama-3.3-70b-versatile on the free
# tier (2026-08-16). These are Groq's recommended replacements. Override with
# the CLASSIFY_MODEL / DRAFT_MODEL environment variables if Groq changes again -
# no code change needed.
CLASSIFY_MODEL = os.environ.get("CLASSIFY_MODEL", "openai/gpt-oss-20b")
DRAFT_MODEL = os.environ.get("DRAFT_MODEL", "openai/gpt-oss-120b")


def get_client() -> Groq:
    global _client
    if _client is None:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY is not set. Get a free key at "
                "https://console.groq.com/keys (no credit card required), "
                "then export it before starting the server, e.g. "
                "`export GROQ_API_KEY=gsk_...`"
            )
        _client = Groq(api_key=api_key)
    return _client


def _extract_json(text: str) -> Optional[dict]:
    """Best-effort extraction of a JSON object from a model response,
    in case it wraps the JSON in prose or a code fence despite instructions."""
    text = text.strip()
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1)
    else:
        brace_match = re.search(r"\{.*\}", text, re.DOTALL)
        if brace_match:
            text = brace_match.group(0)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def complete_json(
    system_prompt: str,
    user_prompt: str,
    model: str = CLASSIFY_MODEL,
    max_tokens: int = 500,
) -> Optional[dict]:
    """Call the model expecting a single JSON object back. Uses Groq's
    native JSON mode as a first line of defense, then retries once with
    a stricter reminder if the response still doesn't parse."""
    # An API key, quota, or transient network failure must not make the whole
    # ticket batch unusable.  Callers already provide safe local fallbacks.
    global last_error
    try:
        client = get_client()
    except Exception as exc:
        last_error = f"{type(exc).__name__}: {exc}"
        return None

    for attempt in range(2):
        prompt = user_prompt
        if attempt == 1:
            prompt += (
                "\n\nYour previous response could not be parsed as JSON. "
                "Respond with ONLY the JSON object - no prose, no code fence."
            )
        response = None
        is_reasoning = model.startswith("openai/gpt-oss")
        kwargs = {}
        if is_reasoning:
            # gpt-oss "thinks" before answering and thinking tokens count toward
            # the limit, so keep effort low and leave plenty of room.
            kwargs["extra_body"] = {"reasoning_effort": "low"}
        for call in range(3):  # retries only for Groq rate limits (HTTP 429)
            try:
                response = client.chat.completions.create(
                    model=model,
                    max_tokens=max(max_tokens, 1200) if is_reasoning else max_tokens,
                    response_format={"type": "json_object"},
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt},
                    ],
                    **kwargs,
                )
                break
            except Exception as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                if "429" in str(exc) and call < 2:
                    time.sleep(6)
                    continue
                return None
        if response is None:
            return None
        text = response.choices[0].message.content or ""
        parsed = _extract_json(text)
        if parsed is not None:
            return parsed

    return None