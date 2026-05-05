from __future__ import annotations

from datetime import datetime

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.email.application.port.email_repository_port import EmailRepositoryPort
from app.domains.email.domain.entity.email import Email
from app.domains.email.domain.value_object.email_source import EmailSource
from app.domains.email.domain.value_object.parsed_status import ParsedStatus
from app.domains.email.infrastructure.mapper.email_mapper import to_entity, to_orm
from app.domains.email.infrastructure.orm.email_orm import EmailORM


class EmailRepository(EmailRepositoryPort):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def save(self, email: Email) -> Email:
        orm = to_orm(email)
        self._session.add(orm)
        await self._session.flush()
        await self._session.refresh(orm)
        return to_entity(orm)

    async def find_by_message_id(
        self, *, source: EmailSource, account: str, message_id: str
    ) -> Email | None:
        stmt = select(EmailORM).where(
            EmailORM.source == str(source),
            EmailORM.account == account,
            EmailORM.message_id == message_id,
        )
        orm = (await self._session.execute(stmt)).scalar_one_or_none()
        return to_entity(orm) if orm else None

    async def list_pending(self, *, user_id: int | None, limit: int = 100) -> list[Email]:
        stmt = (
            select(EmailORM)
            .where(EmailORM.parsed_status == str(ParsedStatus.PENDING))
            .order_by(EmailORM.received_at.asc())
            .limit(limit)
        )
        if user_id is not None:
            stmt = stmt.where(EmailORM.user_id == user_id)
        result = await self._session.execute(stmt)
        return [to_entity(o) for o in result.scalars().all()]

    async def update_parse_status(
        self,
        *,
        email_id: int,
        status: ParsedStatus,
        failure_reason: str | None = None,
    ) -> None:
        orm = await self._session.get(EmailORM, email_id)
        if orm is None:
            return
        orm.parsed_status = str(status)
        orm.parse_failure_reason = failure_reason
        await self._session.flush()

    async def list_by_status(
        self, *, user_id: int | None, status: ParsedStatus, limit: int, offset: int
    ) -> list[Email]:
        stmt = (
            select(EmailORM)
            .where(EmailORM.parsed_status == str(status))
            .order_by(desc(EmailORM.received_at))
            .limit(limit)
            .offset(offset)
        )
        if user_id is not None:
            stmt = stmt.where(EmailORM.user_id == user_id)
        result = await self._session.execute(stmt)
        return [to_entity(o) for o in result.scalars().all()]

    async def latest_received_at(
        self, *, source: EmailSource, account: str, user_id: int | None
    ) -> datetime | None:
        stmt = (
            select(EmailORM.received_at)
            .where(EmailORM.source == str(source), EmailORM.account == account)
            .order_by(desc(EmailORM.received_at))
            .limit(1)
        )
        if user_id is not None:
            stmt = stmt.where(EmailORM.user_id == user_id)
        return (await self._session.execute(stmt)).scalar_one_or_none()
