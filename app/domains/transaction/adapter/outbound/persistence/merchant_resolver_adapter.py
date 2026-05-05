"""merchant 도메인 ``ResolveCanonical`` usecase 호출 wrapper."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.merchant.adapter.outbound.persistence.merchant_alias_repository import (
    MerchantAliasRepository,
)
from app.domains.merchant.application.usecase.resolve_canonical import ResolveCanonical
from app.domains.transaction.application.port.merchant_resolver_port import (
    CanonicalMerchantDto,
    MerchantResolverPort,
)


class MerchantResolverAdapter(MerchantResolverPort):
    def __init__(self, session: AsyncSession):
        self._usecase = ResolveCanonical(MerchantAliasRepository(session))

    async def resolve(self, *, raw_name: str, user_id: int | None) -> CanonicalMerchantDto | None:
        alias = await self._usecase.execute(raw_name, user_id=user_id)
        if alias is None:
            return None
        return CanonicalMerchantDto(
            canonical=alias.canonical,
            category=alias.category.name if alias.category else None,
        )
