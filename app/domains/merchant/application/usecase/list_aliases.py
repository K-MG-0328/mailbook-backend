from __future__ import annotations

from dataclasses import dataclass

from app.domains.merchant.application.port.merchant_alias_repository_port import (
    MerchantAliasRepositoryPort,
)
from app.domains.merchant.domain.entity.merchant_alias import MerchantAlias


@dataclass(slots=True)
class ListAliases:
    repo: MerchantAliasRepositoryPort

    async def execute(self, *, user_id: int | None) -> list[MerchantAlias]:
        return await self.repo.list_all(user_id=user_id)
