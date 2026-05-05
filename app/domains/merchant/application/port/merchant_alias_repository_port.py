from __future__ import annotations

from abc import ABC, abstractmethod

from app.domains.merchant.domain.entity.merchant_alias import MerchantAlias


class MerchantAliasRepositoryPort(ABC):
    @abstractmethod
    async def upsert_by_raw_name(
        self, alias: MerchantAlias, *, user_id: int | None
    ) -> MerchantAlias:
        """``(user_id, raw_name)`` 기준 upsert. 기존 행은 canonical/category/confidence/learned_from 갱신."""

    @abstractmethod
    async def find_by_raw_name(
        self, normalized_raw_name: str, *, user_id: int | None
    ) -> MerchantAlias | None:
        """정규화된 raw_name으로 alias 조회. user_id가 None이면 글로벌 시드(yaml)만 조회."""

    @abstractmethod
    async def list_all(self, *, user_id: int | None) -> list[MerchantAlias]: ...

    @abstractmethod
    async def bulk_seed(self, aliases: list[MerchantAlias]) -> int:
        """yaml 시드용 일괄 upsert. 적재된 행 수 반환."""
