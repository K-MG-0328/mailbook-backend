from __future__ import annotations

from dataclasses import dataclass

from app.domains.transaction.application.port.transaction_repository_port import (
    TransactionRepositoryPort,
)
from app.domains.transaction.domain.entity.transaction import Transaction


@dataclass(slots=True)
class ListTransactions:
    repo: TransactionRepositoryPort

    async def execute(self, *, user_id: int | None, limit: int, offset: int) -> list[Transaction]:
        return await self.repo.list_recent(user_id=user_id, limit=limit, offset=offset)


@dataclass(slots=True)
class ListReviewRequired:
    repo: TransactionRepositoryPort

    async def execute(self, *, user_id: int | None, limit: int, offset: int) -> list[Transaction]:
        return await self.repo.list_review_required(user_id=user_id, limit=limit, offset=offset)
