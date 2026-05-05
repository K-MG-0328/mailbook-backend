from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.domains.merchant.domain.entity.merchant_alias import MerchantAlias


class AliasResponse(BaseModel):
    id: int
    raw_name: str
    canonical: str
    category: str | None
    confidence: float
    learned_from: str
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def from_entity(cls, alias: MerchantAlias) -> AliasResponse:
        if alias.id is None:
            raise ValueError("저장되지 않은 MerchantAlias 는 응답으로 변환할 수 없습니다.")
        return cls(
            id=alias.id,
            raw_name=alias.raw_name,
            canonical=alias.canonical,
            category=alias.category.name if alias.category else None,
            confidence=alias.confidence,
            learned_from=str(alias.learned_from),
            created_at=alias.created_at,
            updated_at=alias.updated_at,
        )
