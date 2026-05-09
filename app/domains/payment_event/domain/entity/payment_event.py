"""``PaymentEvent`` Entity (PRD 2.1 payment_events)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.domains.payment_event.domain.value_object.event_type import EventType

RawData = dict[str, object]


@dataclass(slots=True)
class PaymentEvent:
    email_id: int
    event_type: EventType
    merchant_name: str
    amount: int
    paid_at: datetime
    parser_name: str
    confidence: float
    currency: str = "KRW"  # ISO 4217. amount 단위는 KRW=원, USD=cents.
    card_company: str | None = None
    card_last4: str | None = None
    raw_data: RawData = field(default_factory=dict)
    requires_manual_review: bool = False
    transaction_id: int | None = None
    user_id: int | None = None
    id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
