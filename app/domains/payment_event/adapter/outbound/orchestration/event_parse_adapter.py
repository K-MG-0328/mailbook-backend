"""``EventParsePort`` 구현 — ParsePendingEmails usecase wrapper."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.email.adapter.outbound.orchestration.email_query_adapter import EmailQueryAdapter
from app.domains.email.adapter.outbound.orchestration.email_status_updater_adapter import (
    EmailStatusUpdaterAdapter,
)
from app.domains.email.adapter.outbound.persistence.email_repository import EmailRepository
from app.domains.payment_event.adapter.outbound.external.anthropic_llm_parser import (
    AnthropicLlmParser,
)
from app.domains.payment_event.adapter.outbound.parsers.provider import StaticParserProvider
from app.domains.payment_event.adapter.outbound.persistence.payment_event_repository import (
    PaymentEventRepository,
)
from app.domains.payment_event.application.usecase.parse_pending_emails import ParsePendingEmails
from app.domains.transaction.application.port.event_parse_port import (
    EventParsePort,
    EventParseSummaryDto,
)


class EventParseAdapter(EventParsePort):
    def __init__(self, session: AsyncSession):
        email_repo = EmailRepository(session)
        self._usecase = ParsePendingEmails(
            email_query=EmailQueryAdapter(email_repo),
            email_updater=EmailStatusUpdaterAdapter(email_repo),
            parser_provider=StaticParserProvider(),
            payment_event_repo=PaymentEventRepository(session),
            llm_parser=AnthropicLlmParser(),
        )

    async def parse_pending(self, *, user_id: int | None, limit: int) -> EventParseSummaryDto:
        summary = await self._usecase.execute(user_id=user_id, limit=limit)
        return EventParseSummaryDto(
            parsed=summary.parsed,
            skipped=summary.skipped,
            failed=summary.failed,
            llm_invoked=summary.llm_invoked,
        )
