"""
ORM model (single denormalized Ticket table - simplest thing that works
for a hackathon scope) and the Pydantic schemas the API returns.
"""
import json
from datetime import datetime
from typing import Optional, List

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text
)
from pydantic import BaseModel, ConfigDict

from app.database import Base


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)

    # Raw ingested fields
    sender_email = Column(String, nullable=False)
    sender_name = Column(String, nullable=True)
    subject = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    timestamp = Column(DateTime, nullable=True)
    is_vip = Column(Boolean, default=False)

    # Classification (filled by services/classification.py)
    category = Column(String, nullable=True)          # billing, bug, complaint, request, praise, other
    urgency = Column(Integer, nullable=True)           # 1-5
    sentiment = Column(String, nullable=True)          # positive, neutral, negative
    sentiment_score = Column(Float, nullable=True)     # -1..1, negative = worse
    confidence = Column(Float, nullable=True)          # 0-1, the model's own confidence in this classification
    needs_review = Column(Boolean, default=False)      # True when confidence falls below the review threshold

    # Embedding + dedup (filled by services/embeddings.py, dedup.py)
    embedding_json = Column(Text, nullable=True)        # JSON-encoded list[float]
    cluster_id = Column(Integer, nullable=True)         # tickets in the same cluster share this

    # Prioritization (filled by services/prioritization.py)
    priority_score = Column(Float, nullable=True)

    # Action + draft (filled by services/draft_generator.py)
    action_type = Column(String, nullable=True)        # refund, escalate, answer_faq, forward, no_action
    draft_reply = Column(Text, nullable=True)

    # Human-in-the-loop status
    status = Column(String, default="new")             # new -> triaged -> approved | rejected
    final_reply = Column(Text, nullable=True)           # set if a human edits the draft before approving
    decided_at = Column(DateTime, nullable=True)        # when a human approved/rejected this ticket

    def set_embedding(self, vec: List[float]):
        self.embedding_json = json.dumps(vec)

    def get_embedding(self) -> Optional[List[float]]:
        if not self.embedding_json:
            return None
        return json.loads(self.embedding_json)


# ---- Pydantic schemas (API request/response shapes) ----

class TicketOut(BaseModel):
    id: int
    sender_email: str
    sender_name: Optional[str] = None
    subject: str
    body: str
    timestamp: Optional[datetime] = None
    is_vip: bool

    category: Optional[str] = None
    urgency: Optional[int] = None
    sentiment: Optional[str] = None
    sentiment_score: Optional[float] = None
    confidence: Optional[float] = None
    needs_review: bool = False

    cluster_id: Optional[int] = None
    cluster_size: Optional[int] = None  # computed, not stored

    priority_score: Optional[float] = None

    action_type: Optional[str] = None
    draft_reply: Optional[str] = None

    status: str
    final_reply: Optional[str] = None
    decided_at: Optional[datetime] = None

    # Computed at response time from services/sla.py - never stored, since
    # "hours remaining" changes every time you look at it.
    sla_target_hours: Optional[float] = None
    sla_hours_remaining: Optional[float] = None
    sla_breached: bool = False
    sla_risk: float = 0.0

    model_config = ConfigDict(from_attributes=True)


class TicketDecision(BaseModel):
    """Body for approving/rejecting a ticket from the dashboard."""
    status: str                       # "approved" or "rejected"
    final_reply: Optional[str] = None  # human-edited reply, if changed


class PipelineStatus(BaseModel):
    total: int
    ingested: int
    classified: int
    embedded: int
    prioritized: int
    drafted: int
    done: bool


class ClusterResolution(BaseModel):
    """Body for resolving every ticket in a duplicate cluster at once."""
    status: str                        # "approved" or "rejected"
    final_reply: Optional[str] = None   # applied to every ticket in the cluster


class InsightsOut(BaseModel):
    total: int
    by_category: dict
    by_sentiment: dict
    by_status: dict
    needs_review_count: int
    sla_breached_count: int
    sla_at_risk_count: int      # risk >= 0.75 but not yet breached
    cluster_count: int
    avg_priority: Optional[float] = None
