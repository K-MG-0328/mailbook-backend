"""``EmailFetchPort`` 구현. FetchEmails usecase + GmailConnector 조합."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.email.adapter.outbound.external.gmail_connector import GmailConnector
from app.domains.email.adapter.outbound.persistence.email_repository import EmailRepository
from app.domains.email.adapter.outbound.persistence.encrypted_token_storage import (
    EncryptedTokenStorage,
)
from app.domains.email.application.usecase.fetch_emails import FetchEmails
from app.domains.transaction.application.port.email_fetch_port import EmailFetchPort


class GmailFetchAdapter(EmailFetchPort):
    def __init__(self, session: AsyncSession):
        token_storage = EncryptedTokenStorage(session)
        connector = GmailConnector(token_storage=token_storage)
        repo = EmailRepository(session)
        self._usecase = FetchEmails(connector=connector, repo=repo)

    async def fetch(
        self,
        *,
        account: str,
        since: datetime | None,
        until: datetime | None,
        user_id: int | None,
    ) -> int:
        return await self._usecase.execute(
            account=account, since=since, until=until, user_id=user_id
        )
