from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.domains.transaction.domain.value_object.payment_method import PaymentMethod


@dataclass(slots=True)
class Transaction:
    """가계부 1줄 (PRD 2.1 transactions)."""

    merchant_name: str
    amount: int
    paid_at: datetime
    payment_method: PaymentMethod = PaymentMethod.UNKNOWN
    canonical_merchant: str | None = None
    category: str | None = None
    card_company: str | None = None
    card_last4: str | None = None
    note: str | None = None
    is_verified: bool = False
    requires_manual_review: bool = False
    user_id: int | None = None
    id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
