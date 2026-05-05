from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.merchant.application.port.merchant_alias_repository_port import (
    MerchantAliasRepositoryPort,
)
from app.domains.merchant.domain.entity.merchant_alias import MerchantAlias
from app.domains.merchant.infrastructure.mapper.merchant_alias_mapper import to_entity, to_orm
from app.domains.merchant.infrastructure.orm.merchant_alias_orm import MerchantAliasORM


class MerchantAliasRepository(MerchantAliasRepositoryPort):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def upsert_by_raw_name(
        self, alias: MerchantAlias, *, user_id: int | None
    ) -> MerchantAlias:
        existing = await self._find_orm(alias.raw_name, user_id=user_id)
        if existing is None:
            orm = to_orm(alias)
            orm.user_id = user_id
            self._session.add(orm)
            await self._session.flush()
            await self._session.refresh(orm)
            return to_entity(orm)

        existing.canonical = alias.canonical
        existing.category = alias.category.name if alias.category else None
        existing.confidence = alias.confidence
        existing.learned_from = str(alias.learned_from)
        await self._session.flush()
        await self._session.refresh(existing)
        return to_entity(existing)

    async def find_by_raw_name(
        self, normalized_raw_name: str, *, user_id: int | None
    ) -> MerchantAlias | None:
        orm = await self._find_orm(normalized_raw_name, user_id=user_id)
        return to_entity(orm) if orm else None

    async def _find_orm(
        self, normalized_raw_name: str, *, user_id: int | None
    ) -> MerchantAliasORM | None:
        stmt = select(MerchantAliasORM).where(
            MerchantAliasORM.raw_name == normalized_raw_name,
            MerchantAliasORM.user_id.is_(None)
            if user_id is None
            else MerchantAliasORM.user_id == user_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(self, *, user_id: int | None) -> list[MerchantAlias]:
        stmt = select(MerchantAliasORM).where(
            MerchantAliasORM.user_id.is_(None)
            if user_id is None
            else MerchantAliasORM.user_id == user_id,
        )
        result = await self._session.execute(stmt)
        return [to_entity(o) for o in result.scalars().all()]

    async def bulk_seed(self, aliases: list[MerchantAlias]) -> int:
        if not aliases:
            return 0
        rows = [
            {
                "user_id": a.user_id,
                "raw_name": a.raw_name,
                "canonical": a.canonical,
                "category": a.category.name if a.category else None,
                "confidence": a.confidence,
                "learned_from": str(a.learned_from),
            }
            for a in aliases
        ]
        # Postgres 한정 ON CONFLICT (uq_merchant_aliases_user_raw)
        stmt = pg_insert(MerchantAliasORM).values(rows)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_merchant_aliases_user_raw",
            set_={
                "canonical": stmt.excluded.canonical,
                "category": stmt.excluded.category,
                "confidence": stmt.excluded.confidence,
                "learned_from": stmt.excluded.learned_from,
            },
        )
        await self._session.execute(stmt)
        await self._session.flush()
        return len(rows)
