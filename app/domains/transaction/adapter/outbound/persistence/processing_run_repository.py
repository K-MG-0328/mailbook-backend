from __future__ import annotations

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.transaction.application.port.processing_run_repository_port import (
    ProcessingRunRepositoryPort,
)
from app.domains.transaction.domain.entity.processing_run import ProcessingRun
from app.domains.transaction.infrastructure.mapper.processing_run_mapper import to_entity, to_orm
from app.domains.transaction.infrastructure.orm.transaction_orm import ProcessingRunORM


class ProcessingRunRepository(ProcessingRunRepositoryPort):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, run: ProcessingRun) -> ProcessingRun:
        orm = to_orm(run)
        self._session.add(orm)
        await self._session.flush()
        await self._session.refresh(orm)
        return to_entity(orm)

    async def update(self, run: ProcessingRun) -> ProcessingRun:
        if run.id is None:
            raise ValueError("update 는 id 가 있는 ProcessingRun 만 가능합니다.")
        orm = await self._session.get(ProcessingRunORM, run.id)
        if orm is None:
            raise ValueError(f"ProcessingRun {run.id} 가 존재하지 않습니다.")
        orm.finished_at = run.finished_at
        orm.emails_fetched = run.emails_fetched
        orm.events_parsed = run.events_parsed
        orm.transactions_created = run.transactions_created
        orm.errors = run.errors if run.errors else None
        await self._session.flush()
        await self._session.refresh(orm)
        return to_entity(orm)

    async def list_recent(self, *, user_id: int | None, limit: int) -> list[ProcessingRun]:
        stmt = select(ProcessingRunORM).order_by(desc(ProcessingRunORM.started_at)).limit(limit)
        if user_id is not None:
            stmt = stmt.where(ProcessingRunORM.user_id == user_id)
        result = await self._session.execute(stmt)
        return [to_entity(o) for o in result.scalars().all()]
