"""``ParseResult`` 값 객체 (PRD 2.4 인터페이스 계약 준수)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.domains.payment_event.domain.value_object.event_type import EventType

RawData = dict[str, object]


@dataclass(slots=True)
class ParseResult:
    success: bool
    parser_name: str
    event_type: EventType | None = None
    merchant_name: str = ""
    amount: int = 0  # 원 단위 정수
    paid_at: datetime | None = None  # KST timezone-aware
    card_company: str | None = None
    card_last4: str | None = None
    confidence: float = 0.0
    raw_data: RawData = field(default_factory=dict)
    failure_reason: str | None = None

    @classmethod
    def fail(cls, *, parser_name: str, reason: str) -> "ParseResult":
        return cls(success=False, parser_name=parser_name, failure_reason=reason)
