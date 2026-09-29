"""
Priority scoring. Deliberately a plain weighted formula, not another LLM
call - judges (and real support leads) trust a number they can audit
over a black-box "the AI decided" score. Weights are named constants so
they're easy to defend and tune live.

priority = W_URGENCY   * urgency (1-5, normalized to 0-1)
         + W_SENTIMENT  * negativity (0-1, more negative = higher)
         + W_VIP        * is_vip (0 or 1)
         + W_CLUSTER    * cluster_size_boost (0-1, bigger incidents surface higher)
         + W_SLA        * sla_risk (0-1, how close/past the response-time deadline)
"""
from typing import List
from app.models import Ticket
from app.services.sla import compute_sla

W_URGENCY = 0.35
W_SENTIMENT = 0.20
W_VIP = 0.15
W_CLUSTER = 0.10
W_SLA = 0.20

MAX_CLUSTER_BOOST_SIZE = 5  # a cluster of 5+ duplicates maxes out this term


def score_ticket(ticket: Ticket, cluster_size: int) -> float:
    urgency_norm = (ticket.urgency or 3) / 5.0
    negativity_norm = max(0.0, -(ticket.sentiment_score or 0.0))  # only negative sentiment adds urgency
    vip_norm = 1.0 if ticket.is_vip else 0.0
    cluster_norm = min(cluster_size, MAX_CLUSTER_BOOST_SIZE) / MAX_CLUSTER_BOOST_SIZE
    sla_norm = compute_sla(ticket.category, ticket.timestamp)["risk"]

    score = (
        W_URGENCY * urgency_norm
        + W_SENTIMENT * negativity_norm
        + W_VIP * vip_norm
        + W_CLUSTER * cluster_norm
        + W_SLA * sla_norm
    )
    return round(score, 4)


def prioritize_tickets(tickets: List[Ticket], cluster_sizes: dict) -> None:
    """Sets `priority_score` on each ticket in place."""
    for ticket in tickets:
        size = cluster_sizes.get(ticket.cluster_id, 1)
        ticket.priority_score = score_ticket(ticket, size)
