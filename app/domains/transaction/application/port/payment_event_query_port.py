"""transaction 도메인이 payment_event 도메인을 anti-corruption 으로 조회/갱신."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class CandidateEventDto:
    """매칭 엔진이 사용하는 최소 표면. PaymentEvent 의 일부 컬럼만 노출."""

    id: int
    event_type: str  # "merchant_receipt" | "card_notification"
    merchant_name: str
    amount: int
    currency: str  # ISO 4217. amount 해석 단위 (KRW=원, USD=cents).
    paid_at: datetime
    card_company: str | None
    card_last4: str | None
    transaction_id: int | None
    user_id: int | None


class PaymentEventQueryPort(ABC):
    @abstractmethod
    async def list_unmatched(
        self, *, user_id: int | None, limit: int
    ) -> list[CandidateEventDto]: ...

    @abstractmethod
    async def find_candidates(
        self,
        *,
        opposite_event_type: str,
        amount: int,
        center: datetime,
        window_minutes: int,
        user_id: int | None,
    ) -> list[CandidateEventDto]: ...

    @abstractmethod
    async def list_unmatched_older_than(
        self, *, before: datetime, user_id: int | None, limit: int
    ) -> list[CandidateEventDto]: ...

    @abstractmethod
    async def assign_transaction(self, *, event_ids: list[int], transaction_id: int) -> None: ...
