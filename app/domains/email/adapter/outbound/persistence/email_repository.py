from __future__ import annotations

from datetime import datetime

from sqlalchemy import desc, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
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
        # INSERT ... ON CONFLICT DO NOTHING (uq_emails_source_account_msg).
        # 동일 message_id 가 이미 있으면 새 row 안 넣고 기존 row 를 SELECT 해 반환.
        orm = to_orm(email)
        values = {
            "user_id": orm.user_id,
            "source": orm.source,
            "account": orm.account,
            "message_id": orm.message_id,
            "sender": orm.sender,
            "subject": orm.subject,
            "received_at": orm.received_at,
            "body_text": orm.body_text,
            "body_html": orm.body_html,
            "labels": orm.labels,
            "parsed_status": orm.parsed_status,
            "parse_failure_reason": orm.parse_failure_reason,
        }
        stmt = (
            pg_insert(EmailORM)
            .values(**values)
            .on_conflict_do_nothing(constraint="uq_emails_source_account_msg")
            .returning(EmailORM.id)
        )
        result = await self._session.execute(stmt)
        inserted_id = result.scalar_one_or_none()
        if inserted_id is None:
            existing = await self.find_by_message_id(
                source=email.source, account=email.account, message_id=email.message_id
            )
            if existing is None:
                raise RuntimeError(
                    f"INSERT 충돌인데 SELECT 도 못 찾음: {email.source}/{email.account}/{email.message_id}"
                )
            return existing
        loaded = await self._session.get(EmailORM, inserted_id)
        if loaded is None:
            raise RuntimeError(f"INSERT 직후 row 조회 실패: id={inserted_id}")
        return to_entity(loaded)

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
