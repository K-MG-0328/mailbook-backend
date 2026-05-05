from __future__ import annotations

from dataclasses import dataclass

from app.common.exception.app_exception import AppException
from app.domains.transaction.application.port.transaction_repository_port import (
    TransactionRepositoryPort,
)
from app.domains.transaction.domain.entity.transaction import Transaction


@dataclass(slots=True)
class VerifyTransaction:
    repo: TransactionRepositoryPort

    async def execute(
        self, *, transaction_id: int, is_verified: bool, note: str | None
    ) -> Transaction:
        updated = await self.repo.update_verified(
            transaction_id=transaction_id, is_verified=is_verified, note=note
        )
        if updated is None:
            raise AppException(
                status_code=404, message=f"Transaction {transaction_id} 가 존재하지 않습니다."
            )
        return updated
