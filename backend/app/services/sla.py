"""
SLA (response-time target) tracking per ticket category. This is what
lets a ticket that's quietly approaching its deadline get surfaced
before it actually breaches, instead of only reacting after the fact.

Targets are illustrative defaults for the demo - in a real deployment
these would come from the company's actual support policy.
"""
from datetime import datetime, timezone
from typing import Optional, TypedDict

SLA_HOURS_BY_CATEGORY = {
    "account_access": 4,
    "billing": 12,
    "bug": 24,
    "complaint": 8,
    "question": 48,
    "feature_request": 120,
    "praise": 168,
    "other": 24,
}
DEFAULT_SLA_HOURS = 24


class SlaStatus(TypedDict):
    target_hours: float
    hours_remaining: Optional[float]
    breached: bool
    risk: float  # 0-1, 1.0 = at or past the deadline


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        # CSV exports often omit a timezone. Interpret those values in the
        # server's local timezone (the same convention used by datetime.now)
        # before converting, rather than silently treating local time as UTC.
        return dt.astimezone().astimezone(timezone.utc)
    return dt.astimezone(timezone.utc)


def compute_sla(category: Optional[str], created_at: Optional[datetime], now: Optional[datetime] = None) -> SlaStatus:
    target = SLA_HOURS_BY_CATEGORY.get(category, DEFAULT_SLA_HOURS)

    if created_at is None:
        # No timestamp to measure against - assume fresh, zero risk rather
        # than guessing a false alarm.
        return SlaStatus(target_hours=target, hours_remaining=target, breached=False, risk=0.0)

    now = _as_utc(now) if now else datetime.now(timezone.utc)
    created = _as_utc(created_at)

    elapsed_hours = (now - created).total_seconds() / 3600.0
    remaining = target - elapsed_hours
    risk = max(0.0, min(1.0, elapsed_hours / target)) if target > 0 else 0.0

    return SlaStatus(
        target_hours=target,
        hours_remaining=round(remaining, 1),
        breached=remaining < 0,
        risk=round(risk, 4),
    )
