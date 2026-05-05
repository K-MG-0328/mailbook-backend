"""``EmailConnectorPort`` (PRD 2.4 EmailConnector 인터페이스 계약).

source_name / authenticate / fetch_emails(since, until) / apply_label.
구체 구현은 ``adapter/outbound/external/gmail_connector.py`` 등.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from datetime import datetime

from app.domains.email.domain.entity.email import Email


class EmailConnectorPort(ABC):
    source_name: str  # 식별자 (예: 'gmail')

    @abstractmethod
    async def authenticate(self, *, account: str, user_id: int | None) -> None:
        """인증 수행. 실패 시 예외."""

    @abstractmethod
    def fetch_emails(
        self,
        *,
        account: str,
        since: datetime | None,
        until: datetime | None,
        user_id: int | None,
    ) -> AsyncIterator[Email]:
        """기간 내 이메일을 순차 반환. 호출자는 ``async for`` 로 소비.

        구현은 async generator function (``async def`` + ``yield``) 으로 작성하면
        반환 타입이 자동으로 AsyncIterator 가 된다.
        """

    @abstractmethod
    async def apply_label(
        self, *, account: str, message_id: str, label: str, user_id: int | None
    ) -> None: ...
