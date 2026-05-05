from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response.base_response import BaseResponse
from app.domains.merchant.adapter.outbound.persistence.merchant_alias_repository import (
    MerchantAliasRepository,
)
from app.domains.merchant.application.request.learn_alias_request import LearnAliasRequest
from app.domains.merchant.application.response.alias_response import AliasResponse
from app.domains.merchant.application.response.category_response import CategoryListResponse
from app.domains.merchant.application.usecase.learn_alias import LearnAlias
from app.domains.merchant.application.usecase.list_aliases import ListAliases
from app.domains.merchant.application.usecase.seed_from_yaml import SeedFromYaml
from app.domains.merchant.domain.value_object.learned_from import LearnedFrom
from app.domains.merchant.infrastructure.yaml_loader.categories_yaml_loader import (
    YamlCategoryCatalog,
)
from app.domains.merchant.infrastructure.yaml_loader.merchants_yaml_loader import (
    load_merchants_yaml,
)
from app.infrastructure.config.settings import get_settings
from app.infrastructure.database.database import get_db

router = APIRouter(prefix="/merchants", tags=["merchants"])

# 백엔드 root 의 config/ 디렉토리를 기본으로 사용
_CONFIG_DIR = Path(__file__).resolve().parents[5] / "config"
_DEFAULT_MERCHANTS_YAML = _CONFIG_DIR / "merchants.yaml"
_DEFAULT_CATEGORIES_YAML = _CONFIG_DIR / "categories.yaml"


def get_category_catalog() -> YamlCategoryCatalog:
    return YamlCategoryCatalog(_DEFAULT_CATEGORIES_YAML)


SessionDep = Annotated[AsyncSession, Depends(get_db)]
CatalogDep = Annotated[YamlCategoryCatalog, Depends(get_category_catalog)]


@router.get("/categories", response_model=BaseResponse[CategoryListResponse])
async def list_categories(catalog: CatalogDep) -> BaseResponse[CategoryListResponse]:
    return BaseResponse.ok(
        data=CategoryListResponse(categories=[c.name for c in catalog.list_categories()])
    )


@router.get("/aliases", response_model=BaseResponse[list[AliasResponse]])
async def list_aliases_endpoint(
    session: SessionDep,
    user_scope: Annotated[
        bool, Query(description="True: 본인 알리아스만, False: 글로벌 시드")
    ] = True,
) -> BaseResponse[list[AliasResponse]]:
    settings = get_settings()
    user_id = settings.owner_user_id if user_scope else None
    aliases = await ListAliases(MerchantAliasRepository(session)).execute(user_id=user_id)
    return BaseResponse.ok(data=[AliasResponse.from_entity(a) for a in aliases])


@router.post("/aliases", response_model=BaseResponse[AliasResponse])
async def learn_alias_endpoint(
    payload: LearnAliasRequest,
    session: SessionDep,
    catalog: CatalogDep,
) -> BaseResponse[AliasResponse]:
    settings = get_settings()
    usecase = LearnAlias(MerchantAliasRepository(session), catalog)
    alias = await usecase.execute(
        raw_name=payload.raw_name,
        canonical=payload.canonical,
        category=payload.category,
        confidence=payload.confidence,
        learned_from=LearnedFrom.MANUAL,
        user_id=settings.owner_user_id,
    )
    await session.commit()
    return BaseResponse.ok(data=AliasResponse.from_entity(alias))


@router.post("/seed", response_model=BaseResponse[dict[str, int]])
async def seed_from_yaml_endpoint(
    session: SessionDep,
    catalog: CatalogDep,
) -> BaseResponse[dict[str, int]]:
    rows = load_merchants_yaml(_DEFAULT_MERCHANTS_YAML)
    usecase = SeedFromYaml(MerchantAliasRepository(session), catalog)
    inserted = await usecase.execute(rows)
    await session.commit()
    return BaseResponse.ok(data={"seeded": inserted})
