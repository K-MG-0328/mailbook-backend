"""카테고리 값 객체.

PRD 8.4: 허용된 카테고리만 사용. 분류기는 반드시 이 목록 중 하나를 반환.
도메인은 카테고리 목록을 알지 못한다 — Application이 ``CategoryCatalogPort``로 주입한다.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Category:
    """카테고리명을 감싸는 단순 값 객체. 동일성은 ``name`` 만으로 결정된다."""

    name: str

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("Category.name 은 비어 있을 수 없습니다.")
