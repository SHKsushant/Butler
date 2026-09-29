from datetime import datetime, timedelta, timezone

from app.services.sla import compute_sla, SLA_HOURS_BY_CATEGORY, DEFAULT_SLA_HOURS


def test_fresh_ticket_has_zero_risk():
    now = datetime.now(timezone.utc)
    sla = compute_sla("bug", now)
    assert sla["risk"] == 0.0
    assert not sla["breached"]
    assert sla["hours_remaining"] == SLA_HOURS_BY_CATEGORY["bug"]


def test_ticket_past_deadline_is_breached():
    target = SLA_HOURS_BY_CATEGORY["account_access"]
    created = datetime.now(timezone.utc) - timedelta(hours=target + 2)
    sla = compute_sla("account_access", created)
    assert sla["breached"] is True
    assert sla["hours_remaining"] < 0
    assert sla["risk"] == 1.0  # risk is clamped at 1.0, not unbounded


def test_ticket_halfway_to_deadline_has_partial_risk():
    target = SLA_HOURS_BY_CATEGORY["billing"]
    created = datetime.now(timezone.utc) - timedelta(hours=target / 2)
    sla = compute_sla("billing", created)
    assert 0.4 < sla["risk"] < 0.6
    assert not sla["breached"]


def test_unknown_category_falls_back_to_default_target():
    sla = compute_sla("some_new_category_not_in_the_table", datetime.now(timezone.utc))
    assert sla["target_hours"] == DEFAULT_SLA_HOURS


def test_missing_timestamp_assumes_zero_risk_rather_than_guessing():
    sla = compute_sla("bug", None)
    assert sla["risk"] == 0.0
    assert sla["breached"] is False


def test_naive_datetime_is_handled_without_crashing():
    # created_at without tzinfo (e.g. from a CSV without a timezone) should
    # not raise - this guards against a real bug class (naive vs aware
    # datetime comparison raises TypeError in Python).
    naive_past = datetime.now() - timedelta(hours=1)
    sla = compute_sla("bug", naive_past)
    assert sla["risk"] > 0.0
