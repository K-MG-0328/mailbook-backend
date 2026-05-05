"""merchants.yaml → DB 시드. learned_from='yaml' / user_id=NULL 글로벌 행으로 적재."""

from __future__ import annotations

from dataclasses import dataclass

from app.common.exception.app_exception import AppException
from app.domains.merchant.application.port.category_catalog_port import CategoryCatalogPort
from app.domains.merchant.application.port.merchant_alias_repository_port import (
    MerchantAliasRepositoryPort,
)
from app.domains.merchant.application.request.merchant_seed_row import MerchantSeedRow
from app.domains.merchant.domain.entity.merchant_alias import MerchantAlias
from app.domains.merchant.domain.service.alias_resolver import normalize_raw_name
from app.domains.merchant.domain.value_object.category import Category
from app.domains.merchant.domain.value_object.learned_from import LearnedFrom


@dataclass(slots=True)
class SeedFromYaml:
    repo: MerchantAliasRepositoryPort
    category_catalog: CategoryCatalogPort

    async def execute(self, rows: list[MerchantSeedRow]) -> int:
        aliases: list[MerchantAlias] = []
        for row in rows:
            if row.category and not self.category_catalog.is_valid(row.category):
                raise AppException(
                    status_code=500,
                    message=f"merchants.yaml: '{row.canonical}' 의 카테고리 '{row.category}' 는 categories.yaml 에 없습니다.",
                )
            category_vo = Category(row.category) if row.category else None
            for alias_raw in [row.canonical, *row.aliases]:
                aliases.append(
                    MerchantAlias(
                        raw_name=normalize_raw_name(alias_raw),
                        canonical=row.canonical,
                        category=category_vo,
                        confidence=1.0,
                        learned_from=LearnedFrom.YAML,
                        user_id=None,
                    )
                )
        return await self.repo.bulk_seed(aliases)
