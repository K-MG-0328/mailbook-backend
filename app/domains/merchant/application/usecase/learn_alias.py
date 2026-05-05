from __future__ import annotations

from dataclasses import dataclass

from app.common.exception.app_exception import AppException
from app.domains.merchant.application.port.category_catalog_port import CategoryCatalogPort
from app.domains.merchant.application.port.merchant_alias_repository_port import (
    MerchantAliasRepositoryPort,
)
from app.domains.merchant.domain.entity.merchant_alias import MerchantAlias
from app.domains.merchant.domain.service.alias_resolver import normalize_raw_name
from app.domains.merchant.domain.value_object.category import Category
from app.domains.merchant.domain.value_object.learned_from import LearnedFrom


@dataclass(slots=True)
class LearnAlias:
    repo: MerchantAliasRepositoryPort
    category_catalog: CategoryCatalogPort

    async def execute(
        self,
        *,
        raw_name: str,
        canonical: str,
        category: str | None,
        confidence: float,
        learned_from: LearnedFrom,
        user_id: int | None,
    ) -> MerchantAlias:
        if category is not None and not self.category_catalog.is_valid(category):
            raise AppException(status_code=400, message=f"허용되지 않은 카테고리입니다: {category}")

        alias = MerchantAlias(
            raw_name=normalize_raw_name(raw_name),
            canonical=canonical.strip(),
            category=Category(category) if category else None,
            confidence=confidence,
            learned_from=learned_from,
            user_id=user_id,
        )
        return await self.repo.upsert_by_raw_name(alias, user_id=user_id)
