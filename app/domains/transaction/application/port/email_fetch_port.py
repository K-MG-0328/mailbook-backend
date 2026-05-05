"""orchestrator 가 email 도메인 fetch 를 호출하기 위한 anti-corruption 포트."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime


class EmailFetchPort(ABC):
    @abstractmethod
    async def fetch(
        self,
        *,
        account: str,
        since: datetime | None,
        until: datetime | None,
        user_id: int | None,
    ) -> int:
        """저장된 신규 이메일 수 반환."""
