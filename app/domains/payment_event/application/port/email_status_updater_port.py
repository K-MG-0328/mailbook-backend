"""payment_event 가 email.parsed_status 를 갱신하기 위한 anti-corruption 포트."""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import StrEnum


class EmailParsedStatusValue(StrEnum):
    PARSED = "parsed"
    SKIPPED = "skipped"
    FAILED = "failed"


class EmailStatusUpdaterPort(ABC):
    @abstractmethod
    async def update(
        self,
        *,
        email_id: int,
        status: EmailParsedStatusValue,
        failure_reason: str | None,
    ) -> None: ...
