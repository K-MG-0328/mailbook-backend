from __future__ import annotations

from abc import ABC, abstractmethod

from app.domains.payment_event.domain.service.parser import EmailLike
from app.domains.payment_event.domain.value_object.parse_result import ParseResult


class LlmParserPort(ABC):
    """규칙 기반 파서가 처리하지 못한 메일에 대한 LLM 폴백 (PRD 4.1 → 호출 비율 제한)."""

    @abstractmethod
    async def parse(self, email: EmailLike) -> ParseResult: ...
