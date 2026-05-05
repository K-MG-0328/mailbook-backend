"""``PaymentEventQueryPort`` 구현. payment_event ORM 을 같은 세션으로 직접 조회.

이 adapter 는 payment_event 도메인 ORM 을 import 하지만, plan E.5 에 따라 모놀리스
+ 단일 DB 전제에서 허용. 다른 도메인의 application port 만 호출하므로 도메인 결합 0.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.payment_event.infrastructure.orm.payment_event_orm import PaymentEventORM
from app.domains.transaction.application.port.payment_event_query_port import (
    CandidateEventDto,
    PaymentEventQueryPort,
)


class PaymentEventQueryAdapter(PaymentEventQueryPort):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def list_unmatched(self, *, user_id: int | None, limit: int) -> list[CandidateEventDto]:
        stmt = (
            select(PaymentEventORM)
            .where(PaymentEventORM.transaction_id.is_(None))
            .order_by(PaymentEventORM.paid_at.asc())
            .limit(limit)
        )
        if user_id is not None:
            stmt = stmt.where(PaymentEventORM.user_id == user_id)
        result = await self._session.execute(stmt)
        return [_to_dto(o) for o in result.scalars().all()]

    async def find_candidates(
        self,
        *,
        opposite_event_type: str,
        amount: int,
        center: datetime,
        window_minutes: int,
        user_id: int | None,
    ) -> list[CandidateEventDto]:
        delta = timedelta(minutes=window_minutes)
        stmt = (
            select(PaymentEventORM)
            .where(
                PaymentEventORM.event_type == opposite_event_type,
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
        return [_to_dto(o) for o in result.scalars().all()]

    async def list_unmatched_older_than(
        self, *, before: datetime, user_id: int | None, limit: int
    ) -> list[CandidateEventDto]:
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
        return [_to_dto(o) for o in result.scalars().all()]

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


def _to_dto(orm: PaymentEventORM) -> CandidateEventDto:
    return CandidateEventDto(
        id=orm.id,
        event_type=orm.event_type,
        merchant_name=orm.merchant_name,
        amount=orm.amount,
        paid_at=orm.paid_at,
        card_company=orm.card_company,
        card_last4=orm.card_last4,
        transaction_id=orm.transaction_id,
        user_id=orm.user_id,
    )
