from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.domains.transaction.domain.entity.transaction import Transaction


class TransactionResponse(BaseModel):
    id: int
    merchant_name: str
    canonical_merchant: str | None
    amount: int
    paid_at: datetime
    category: str | None
    payment_method: str
    card_company: str | None
    card_last4: str | None
    note: str | None
    is_verified: bool
    requires_manual_review: bool

    @classmethod
    def from_entity(cls, txn: Transaction) -> "TransactionResponse":
        if txn.id is None:
            raise ValueError("저장되지 않은 Transaction 은 응답으로 변환할 수 없습니다.")
        return cls(
            id=txn.id,
            merchant_name=txn.merchant_name,
            canonical_merchant=txn.canonical_merchant,
            amount=txn.amount,
            paid_at=txn.paid_at,
            category=txn.category,
            payment_method=str(txn.payment_method),
            card_company=txn.card_company,
            card_last4=txn.card_last4,
            note=txn.note,
            is_verified=txn.is_verified,
            requires_manual_review=txn.requires_manual_review,
        )


class MatchSummaryResponse(BaseModel):
    matched: int
    review_required: int
    skipped: int


class SoloSummaryResponse(BaseModel):
    subscription: int
    non_card: int
