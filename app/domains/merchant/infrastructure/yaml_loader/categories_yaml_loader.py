"""categories.yaml 로더 + ``CategoryCatalogPort`` 구현."""

from __future__ import annotations

from pathlib import Path

import yaml

from app.domains.merchant.application.port.category_catalog_port import CategoryCatalogPort
from app.domains.merchant.domain.value_object.category import Category


class YamlCategoryCatalog(CategoryCatalogPort):
    def __init__(self, path: str | Path):
        self._path = Path(path)
        self._categories: list[Category] = []
        self._valid_names: set[str] = set()
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        with self._path.open("r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        names = [str(n).strip() for n in raw.get("categories", []) if str(n).strip()]
        self._categories = [Category(name=n) for n in names]
        self._valid_names = {c.name for c in self._categories}

    def list_categories(self) -> list[Category]:
        return list(self._categories)

    def is_valid(self, name: str) -> bool:
        return name in self._valid_names
