from __future__ import annotations

from abc import ABC, abstractmethod

from app.domains.transaction.application.port.payment_event_query_port import CandidateEventDto


class LlmDisambiguatorPort(ABC):
    @abstractmethod
    async def pick(
        self, *, source: CandidateEventDto, candidates: list[CandidateEventDto]
    ) -> int | None:
        """선택된 candidate id 반환. 매칭 불가는 None."""
