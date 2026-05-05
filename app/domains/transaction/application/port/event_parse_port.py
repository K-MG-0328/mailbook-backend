"""orchestrator 가 payment_event 도메인 ParsePendingEmails 를 호출하기 위한 포트."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(slots=True)
class EventParseSummaryDto:
    parsed: int
    skipped: int
    failed: int
    llm_invoked: int


class EventParsePort(ABC):
    @abstractmethod
    async def parse_pending(self, *, user_id: int | None, limit: int) -> EventParseSummaryDto: ...
