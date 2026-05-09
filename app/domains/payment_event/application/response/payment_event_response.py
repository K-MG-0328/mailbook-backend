from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.domains.payment_event.domain.entity.payment_event import PaymentEvent


class PaymentEventResponse(BaseModel):
    id: int
    email_id: int
    transaction_id: int | None
    event_type: str
    merchant_name: str
    amount: int
    currency: str
    paid_at: datetime
    card_company: str | None
    card_last4: str | None
    parser_name: str
    confidence: float
    requires_manual_review: bool

    @classmethod
    def from_entity(cls, event: PaymentEvent) -> "PaymentEventResponse":
        if event.id is None:
            raise ValueError("저장되지 않은 PaymentEvent 는 응답으로 변환할 수 없습니다.")
        return cls(
            id=event.id,
            email_id=event.email_id,
            transaction_id=event.transaction_id,
            event_type=str(event.event_type),
            merchant_name=event.merchant_name,
            amount=event.amount,
            currency=event.currency,
            paid_at=event.paid_at,
            card_company=event.card_company,
            card_last4=event.card_last4,
            parser_name=event.parser_name,
            confidence=event.confidence,
            requires_manual_review=event.requires_manual_review,
        )


class ParseSummaryResponse(BaseModel):
    parsed: int
    skipped: int
    failed: int
    llm_invoked: int
