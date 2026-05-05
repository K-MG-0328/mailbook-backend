"""yaml 시드 행을 표현하는 입력 DTO. Application Layer 위치 (의존성 방향 준수)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class MerchantSeedRow:
    canonical: str
    aliases: list[str] = field(default_factory=list)
    category: str | None = None
