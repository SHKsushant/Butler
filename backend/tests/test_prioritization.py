from datetime import datetime, timezone

from app.models import Ticket
from app.services.prioritization import score_ticket, prioritize_tickets


def make_ticket(**overrides) -> Ticket:
    defaults = dict(
        sender_email="a@example.com",
        subject="Test",
        body="Test body",
        timestamp=datetime.now(timezone.utc),
        is_vip=False,
        category="other",
        urgency=3,
        sentiment_score=0.0,
        cluster_id=1,
    )
    defaults.update(overrides)
    return Ticket(**defaults)


def test_higher_urgency_scores_higher_all_else_equal():
    low = make_ticket(urgency=1)
    high = make_ticket(urgency=5)
    assert score_ticket(high, cluster_size=1) > score_ticket(low, cluster_size=1)


def test_vip_ticket_scores_higher_than_identical_non_vip():
    vip = make_ticket(is_vip=True)
    regular = make_ticket(is_vip=False)
    assert score_ticket(vip, cluster_size=1) > score_ticket(regular, cluster_size=1)


def test_negative_sentiment_increases_score_positive_does_not():
    negative = make_ticket(sentiment_score=-0.8)
    positive = make_ticket(sentiment_score=0.8)
    neutral = make_ticket(sentiment_score=0.0)
    assert score_ticket(negative, cluster_size=1) > score_ticket(neutral, cluster_size=1)
    # positive sentiment shouldn't be penalized below neutral
    assert score_ticket(positive, cluster_size=1) == score_ticket(neutral, cluster_size=1)


def test_larger_cluster_scores_higher():
    ticket = make_ticket()
    assert score_ticket(ticket, cluster_size=5) > score_ticket(ticket, cluster_size=1)


def test_cluster_boost_caps_out_and_does_not_keep_growing():
    ticket = make_ticket()
    score_at_5 = score_ticket(ticket, cluster_size=5)
    score_at_50 = score_ticket(ticket, cluster_size=50)
    assert score_at_5 == score_at_50


def test_score_is_bounded_between_0_and_1():
    worst = make_ticket(urgency=1, is_vip=False, sentiment_score=1.0)
    best = make_ticket(
        urgency=5, is_vip=True, sentiment_score=-1.0,
        category="account_access",
        timestamp=datetime(2000, 1, 1, tzinfo=timezone.utc),  # very overdue -> max SLA risk
    )
    assert 0.0 <= score_ticket(worst, cluster_size=1) <= 1.0
    assert 0.0 <= score_ticket(best, cluster_size=5) <= 1.0


def test_prioritize_tickets_sets_priority_score_on_every_ticket():
    tickets = [make_ticket(cluster_id=i) for i in range(3)]
    sizes = {t.cluster_id: 1 for t in tickets}
    prioritize_tickets(tickets, sizes)
    assert all(t.priority_score is not None for t in tickets)
