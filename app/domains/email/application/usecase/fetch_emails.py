"""Connector → Repository 흐름. 같은 (source, account, message_id)은 멱등 처리."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.domains.email.application.port.email_connector_port import EmailConnectorPort
from app.domains.email.application.port.email_repository_port import EmailRepositoryPort


@dataclass(slots=True)
class FetchEmails:
    connector: EmailConnectorPort
    repo: EmailRepositoryPort

    async def execute(
        self,
        *,
        account: str,
        since: datetime | None,
        until: datetime | None,
        user_id: int | None,
    ) -> int:
        await self.connector.authenticate(account=account, user_id=user_id)
        saved = 0
        async for email in self.connector.fetch_emails(
            account=account, since=since, until=until, user_id=user_id
        ):
            email.user_id = user_id
            existing = await self.repo.find_by_message_id(
                source=email.source, account=email.account, message_id=email.message_id
            )
            if existing is not None:
                continue
            await self.repo.save(email)
            saved += 1
        return saved
