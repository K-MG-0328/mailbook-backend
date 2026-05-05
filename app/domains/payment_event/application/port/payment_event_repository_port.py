from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from app.domains.payment_event.domain.entity.payment_event import PaymentEvent
from app.domains.payment_event.domain.value_object.event_type import EventType


class PaymentEventRepositoryPort(ABC):
    @abstractmethod
    async def save(self, event: PaymentEvent) -> PaymentEvent: ...

    @abstractmethod
    async def find_by_email_id(self, email_id: int) -> PaymentEvent | None: ...

    @abstractmethod
    async def list_unmatched_in_window(
        self,
        *,
        event_type: EventType,
        amount: int,
        center: datetime,
        window_minutes: int,
        user_id: int | None,
    ) -> list[PaymentEvent]:
        """매칭되지 않은(``transaction_id IS NULL``) 후보를 시간 윈도우로 조회 (PRD 2.2 Step 1)."""

    @abstractmethod
    async def list_unmatched_older_than(
        self, *, before: datetime, user_id: int | None, limit: int
    ) -> list[PaymentEvent]:
        """24시간 timeout 처리용 (PRD 2.2 Step 4)."""

    @abstractmethod
    async def list_recent(
        self, *, user_id: int | None, matched: bool | None, limit: int, offset: int
    ) -> list[PaymentEvent]: ...

    @abstractmethod
    async def assign_transaction(self, *, event_ids: list[int], transaction_id: int) -> None: ...
