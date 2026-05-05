from __future__ import annotations

from dataclasses import dataclass

from app.domains.merchant.application.port.merchant_alias_repository_port import (
    MerchantAliasRepositoryPort,
)
from app.domains.merchant.domain.entity.merchant_alias import MerchantAlias
from app.domains.merchant.domain.service.alias_resolver import normalize_raw_name


@dataclass(slots=True)
class ResolveCanonical:
    repo: MerchantAliasRepositoryPort

    async def execute(self, raw_name: str, *, user_id: int | None) -> MerchantAlias | None:
        """raw_name → MerchantAlias. 사용자 알리아스 우선, 없으면 yaml 시드(global) 조회."""
        if not raw_name:
            return None
        normalized = normalize_raw_name(raw_name)
        if user_id is not None:
            user_alias = await self.repo.find_by_raw_name(normalized, user_id=user_id)
            if user_alias is not None:
                return user_alias
        return await self.repo.find_by_raw_name(normalized, user_id=None)
