"""가맹점 → 카테고리 분류. categories.yaml 외 값은 절대 반환하지 않는다 (PRD 8.4)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class CategoryValidator(Protocol):
    def is_valid(self, name: str) -> bool: ...


@dataclass(slots=True)
class Classifier:
    validator: CategoryValidator

    def pick(self, *, alias_category: str | None, fallback: str = "기타") -> str:
        """``MerchantAlias.category`` 가 있으면 검증 후 사용, 없거나 무효면 fallback."""
        if alias_category and self.validator.is_valid(alias_category):
            return alias_category
        if self.validator.is_valid(fallback):
            return fallback
        return ""
