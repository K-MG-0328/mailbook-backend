from __future__ import annotations

from datetime import datetime

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.transaction.application.port.transaction_repository_port import (
    TransactionRepositoryPort,
)
from app.domains.transaction.domain.entity.transaction import Transaction
from app.domains.transaction.infrastructure.mapper.transaction_mapper import to_entity, to_orm
from app.domains.transaction.infrastructure.orm.transaction_orm import TransactionORM


class TransactionRepository(TransactionRepositoryPort):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def save(self, transaction: Transaction) -> Transaction:
        orm = to_orm(transaction)
        self._session.add(orm)
        await self._session.flush()
        await self._session.refresh(orm)
        return to_entity(orm)

    async def get(self, transaction_id: int) -> Transaction | None:
        orm = await self._session.get(TransactionORM, transaction_id)
        return to_entity(orm) if orm else None

    async def list_recent(
        self, *, user_id: int | None, limit: int, offset: int
    ) -> list[Transaction]:
        stmt = (
            select(TransactionORM)
            .order_by(desc(TransactionORM.paid_at))
            .limit(limit)
            .offset(offset)
        )
        if user_id is not None:
            stmt = stmt.where(TransactionORM.user_id == user_id)
        result = await self._session.execute(stmt)
        return [to_entity(o) for o in result.scalars().all()]

    async def list_review_required(
        self, *, user_id: int | None, limit: int, offset: int
    ) -> list[Transaction]:
        stmt = (
            select(TransactionORM)
            .where(TransactionORM.requires_manual_review.is_(True))
            .order_by(desc(TransactionORM.paid_at))
            .limit(limit)
            .offset(offset)
        )
        if user_id is not None:
            stmt = stmt.where(TransactionORM.user_id == user_id)
        result = await self._session.execute(stmt)
        return [to_entity(o) for o in result.scalars().all()]

    async def list_in_period(
        self, *, user_id: int | None, start: datetime, end: datetime
    ) -> list[Transaction]:
        stmt = (
            select(TransactionORM)
            .where(TransactionORM.paid_at >= start, TransactionORM.paid_at < end)
            .order_by(TransactionORM.paid_at.asc())
        )
        if user_id is not None:
            stmt = stmt.where(TransactionORM.user_id == user_id)
        result = await self._session.execute(stmt)
        return [to_entity(o) for o in result.scalars().all()]

    async def update_verified(
        self, *, transaction_id: int, is_verified: bool, note: str | None
    ) -> Transaction | None:
        orm = await self._session.get(TransactionORM, transaction_id)
        if orm is None:
            return None
        orm.is_verified = is_verified
        if note is not None:
            orm.note = note
        if is_verified:
            orm.requires_manual_review = False
        await self._session.flush()
        await self._session.refresh(orm)
        return to_entity(orm)
