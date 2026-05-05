from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.payment_event.application.port.payment_event_repository_port import (
    PaymentEventRepositoryPort,
)
from app.domains.payment_event.domain.entity.payment_event import PaymentEvent
from app.domains.payment_event.domain.value_object.event_type import EventType
from app.domains.payment_event.infrastructure.mapper.payment_event_mapper import to_entity, to_orm
from app.domains.payment_event.infrastructure.orm.payment_event_orm import PaymentEventORM


class PaymentEventRepository(PaymentEventRepositoryPort):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def save(self, event: PaymentEvent) -> PaymentEvent:
        orm = to_orm(event)
        self._session.add(orm)
        await self._session.flush()
        await self._session.refresh(orm)
        return to_entity(orm)

    async def find_by_email_id(self, email_id: int) -> PaymentEvent | None:
        stmt = select(PaymentEventORM).where(PaymentEventORM.email_id == email_id)
        orm = (await self._session.execute(stmt)).scalar_one_or_none()
        return to_entity(orm) if orm else None

    async def list_unmatched_in_window(
        self,
        *,
        event_type: EventType,
        amount: int,
        center: datetime,
        window_minutes: int,
        user_id: int | None,
    ) -> list[PaymentEvent]:
        delta = timedelta(minutes=window_minutes)
        stmt = (
            select(PaymentEventORM)
            .where(
                PaymentEventORM.event_type == str(event_type),
                PaymentEventORM.amount == amount,
                PaymentEventORM.paid_at >= center - delta,
                PaymentEventORM.paid_at <= center + delta,
                PaymentEventORM.transaction_id.is_(None),
            )
            .order_by(PaymentEventORM.paid_at.asc())
        )
        if user_id is not None:
            stmt = stmt.where(PaymentEventORM.user_id == user_id)
        result = await self._session.execute(stmt)
        return [to_entity(o) for o in result.scalars().all()]

    async def list_unmatched_older_than(
        self, *, before: datetime, user_id: int | None, limit: int
    ) -> list[PaymentEvent]:
        stmt = (
            select(PaymentEventORM)
            .where(
                PaymentEventORM.transaction_id.is_(None),
                PaymentEventORM.paid_at <= before,
            )
            .order_by(PaymentEventORM.paid_at.asc())
            .limit(limit)
        )
        if user_id is not None:
            stmt = stmt.where(PaymentEventORM.user_id == user_id)
        result = await self._session.execute(stmt)
        return [to_entity(o) for o in result.scalars().all()]

    async def list_recent(
        self, *, user_id: int | None, matched: bool | None, limit: int, offset: int
    ) -> list[PaymentEvent]:
        stmt = (
            select(PaymentEventORM)
            .order_by(desc(PaymentEventORM.paid_at))
            .limit(limit)
            .offset(offset)
        )
        if matched is True:
            stmt = stmt.where(PaymentEventORM.transaction_id.is_not(None))
        elif matched is False:
            stmt = stmt.where(PaymentEventORM.transaction_id.is_(None))
        if user_id is not None:
            stmt = stmt.where(PaymentEventORM.user_id == user_id)
        result = await self._session.execute(stmt)
        return [to_entity(o) for o in result.scalars().all()]

    async def assign_transaction(self, *, event_ids: list[int], transaction_id: int) -> None:
        if not event_ids:
            return
        stmt = (
            update(PaymentEventORM)
            .where(PaymentEventORM.id.in_(event_ids))
            .values(transaction_id=transaction_id)
        )
        await self._session.execute(stmt)
        await self._session.flush()
