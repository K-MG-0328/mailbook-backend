from __future__ import annotations

from app.domains.merchant.domain.entity.merchant_alias import MerchantAlias
from app.domains.merchant.domain.value_object.category import Category
from app.domains.merchant.domain.value_object.learned_from import LearnedFrom
from app.domains.merchant.infrastructure.orm.merchant_alias_orm import MerchantAliasORM


def to_entity(orm: MerchantAliasORM) -> MerchantAlias:
    return MerchantAlias(
        id=orm.id,
        user_id=orm.user_id,
        raw_name=orm.raw_name,
        canonical=orm.canonical,
        category=Category(orm.category) if orm.category else None,
        confidence=orm.confidence,
        learned_from=LearnedFrom(orm.learned_from),
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


def to_orm(entity: MerchantAlias) -> MerchantAliasORM:
    return MerchantAliasORM(
        user_id=entity.user_id,
        raw_name=entity.raw_name,
        canonical=entity.canonical,
        category=entity.category.name if entity.category else None,
        confidence=entity.confidence,
        learned_from=str(entity.learned_from),
    )
