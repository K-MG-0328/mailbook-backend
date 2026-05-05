from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from app.domains.transaction.domain.entity.transaction import Transaction


class TransactionRepositoryPort(ABC):
    @abstractmethod
    async def save(self, transaction: Transaction) -> Transaction: ...

    @abstractmethod
    async def get(self, transaction_id: int) -> Transaction | None: ...

    @abstractmethod
    async def list_recent(
        self, *, user_id: int | None, limit: int, offset: int
    ) -> list[Transaction]: ...

    @abstractmethod
    async def list_review_required(
        self, *, user_id: int | None, limit: int, offset: int
    ) -> list[Transaction]: ...

    @abstractmethod
    async def list_in_period(
        self, *, user_id: int | None, start: datetime, end: datetime
    ) -> list[Transaction]: ...

    @abstractmethod
    async def update_verified(
        self, *, transaction_id: int, is_verified: bool, note: str | None
    ) -> Transaction | None: ...
