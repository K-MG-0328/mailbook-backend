"""``MerchantAlias`` Entity (PRD 2.1)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.domains.merchant.domain.value_object.category import Category
from app.domains.merchant.domain.value_object.learned_from import LearnedFrom


@dataclass(slots=True)
class MerchantAlias:
    raw_name: str
    canonical: str
    learned_from: LearnedFrom
    category: Category | None = None
    confidence: float = 1.0
    id: int | None = None
    user_id: int | None = None
    created_at: datetime | None = field(default=None)
    updated_at: datetime | None = field(default=None)
