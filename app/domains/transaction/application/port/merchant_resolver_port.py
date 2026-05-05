"""merchant 도메인의 ``ResolveCanonical`` 을 호출하기 위한 anti-corruption 포트."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(slots=True)
class CanonicalMerchantDto:
    canonical: str
    category: str | None


class MerchantResolverPort(ABC):
    @abstractmethod
    async def resolve(
        self, *, raw_name: str, user_id: int | None
    ) -> CanonicalMerchantDto | None: ...
