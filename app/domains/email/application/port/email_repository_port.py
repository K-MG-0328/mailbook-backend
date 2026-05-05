from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from app.domains.email.domain.entity.email import Email
from app.domains.email.domain.value_object.email_source import EmailSource
from app.domains.email.domain.value_object.parsed_status import ParsedStatus


class EmailRepositoryPort(ABC):
    @abstractmethod
    async def save(self, email: Email) -> Email:
        """신규 행 저장. 충돌(UNIQUE) 시 기존 행 반환."""

    @abstractmethod
    async def find_by_message_id(
        self, *, source: EmailSource, account: str, message_id: str
    ) -> Email | None: ...

    @abstractmethod
    async def list_pending(self, *, user_id: int | None, limit: int = 100) -> list[Email]: ...

    @abstractmethod
    async def update_parse_status(
        self,
        *,
        email_id: int,
        status: ParsedStatus,
        failure_reason: str | None = None,
    ) -> None: ...

    @abstractmethod
    async def list_by_status(
        self, *, user_id: int | None, status: ParsedStatus, limit: int, offset: int
    ) -> list[Email]: ...

    @abstractmethod
    async def latest_received_at(
        self, *, source: EmailSource, account: str, user_id: int | None
    ) -> datetime | None: ...
