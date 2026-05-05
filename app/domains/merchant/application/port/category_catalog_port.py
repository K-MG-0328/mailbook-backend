from __future__ import annotations

from abc import ABC, abstractmethod

from app.domains.merchant.domain.value_object.category import Category


class CategoryCatalogPort(ABC):
    """허용된 카테고리 목록 제공자 (categories.yaml 등)."""

    @abstractmethod
    def list_categories(self) -> list[Category]: ...

    @abstractmethod
    def is_valid(self, name: str) -> bool: ...
