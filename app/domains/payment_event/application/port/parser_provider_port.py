from __future__ import annotations

from abc import ABC, abstractmethod

from app.domains.payment_event.domain.service.parser import Parser


class ParserProviderPort(ABC):
    """등록된 모든 파서 인스턴스를 노출. yaml 라우팅 + 파일 시스템 등록을 모두 책임."""

    @abstractmethod
    def list_parsers(self) -> list[Parser]: ...
