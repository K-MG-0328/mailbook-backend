from __future__ import annotations

from app.domains.email.adapter.outbound.persistence.email_repository import EmailRepository
from app.domains.email.domain.value_object.parsed_status import ParsedStatus
from app.domains.payment_event.application.port.email_status_updater_port import (
    EmailParsedStatusValue,
    EmailStatusUpdaterPort,
)


class EmailStatusUpdaterAdapter(EmailStatusUpdaterPort):
    def __init__(self, repo: EmailRepository):
        self._repo = repo

    async def update(
        self,
        *,
        email_id: int,
        status: EmailParsedStatusValue,
        failure_reason: str | None,
    ) -> None:
        await self._repo.update_parse_status(
            email_id=email_id,
            status=ParsedStatus(str(status)),
            failure_reason=failure_reason,
        )
