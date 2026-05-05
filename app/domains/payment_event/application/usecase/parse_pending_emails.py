"""규칙 기반 파서 라우팅 → 실패 시 LLM 폴백 → PaymentEvent 저장 + email status 갱신.

본문이 비어있는 메일(첨부 위주)은 SKIPPED. PRD 7: LLM 응답 파싱 실패 retry 1회 후 FAILED.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from app.domains.payment_event.application.port.email_query_port import EmailQueryPort
from app.domains.payment_event.application.port.email_status_updater_port import (
    EmailParsedStatusValue,
    EmailStatusUpdaterPort,
)
from app.domains.payment_event.application.port.llm_parser_port import LlmParserPort
from app.domains.payment_event.application.port.parser_provider_port import ParserProviderPort
from app.domains.payment_event.application.port.payment_event_repository_port import (
    PaymentEventRepositoryPort,
)
from app.domains.payment_event.application.request.pending_email import PendingEmail
from app.domains.payment_event.domain.entity.payment_event import PaymentEvent
from app.domains.payment_event.domain.service.parser import Parser
from app.domains.payment_event.domain.service.parser_registry import select_parser
from app.domains.payment_event.domain.value_object.parse_result import ParseResult

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ParseResultSummary:
    parsed: int
    skipped: int
    failed: int
    llm_invoked: int


@dataclass(slots=True)
class ParsePendingEmails:
    email_query: EmailQueryPort
    email_updater: EmailStatusUpdaterPort
    parser_provider: ParserProviderPort
    payment_event_repo: PaymentEventRepositoryPort
    llm_parser: LlmParserPort

    async def execute(self, *, user_id: int | None, limit: int = 100) -> ParseResultSummary:
        emails = await self.email_query.list_pending(user_id=user_id, limit=limit)
        parsers = self.parser_provider.list_parsers()

        summary = ParseResultSummary(parsed=0, skipped=0, failed=0, llm_invoked=0)

        for email in emails:
            outcome = await self._process_one(
                email=email, parsers=parsers, user_id=user_id, summary=summary
            )
            if outcome is not None:
                await self.payment_event_repo.save(outcome)

        return summary

    async def _process_one(
        self,
        *,
        email: PendingEmail,
        parsers: list[Parser],
        user_id: int | None,
        summary: ParseResultSummary,
    ) -> PaymentEvent | None:
        if not email.body_text and not email.body_html:
            await self.email_updater.update(
                email_id=email.id,
                status=EmailParsedStatusValue.SKIPPED,
                failure_reason="본문이 비어있음 (첨부 위주 또는 이미지 메일)",
            )
            summary.skipped += 1
            return None

        parser = select_parser(parsers, email)
        if parser is not None:
            try:
                result = parser.parse(email)
            except Exception as exc:
                logger.exception("파서 '%s' 예외", parser.name)
                result = ParseResult.fail(parser_name=parser.name, reason=f"파서 예외: {exc}")
        else:
            result = await self._invoke_llm(email)
            summary.llm_invoked += 1

        if not result.success:
            # 규칙 기반이 실패했고 LLM 폴백이 아직이면 한번 시도
            if parser is not None:
                result = await self._invoke_llm(email)
                summary.llm_invoked += 1

        if not result.success:
            await self.email_updater.update(
                email_id=email.id,
                status=EmailParsedStatusValue.FAILED,
                failure_reason=result.failure_reason or "파싱 실패",
            )
            summary.failed += 1
            return None

        # 성공
        if result.event_type is None or result.paid_at is None:
            await self.email_updater.update(
                email_id=email.id,
                status=EmailParsedStatusValue.FAILED,
                failure_reason="ParseResult.success=True 이지만 event_type/paid_at 누락",
            )
            summary.failed += 1
            return None

        event = PaymentEvent(
            email_id=email.id,
            event_type=result.event_type,
            merchant_name=result.merchant_name,
            amount=result.amount,
            paid_at=result.paid_at,
            card_company=result.card_company,
            card_last4=result.card_last4,
            raw_data=result.raw_data,
            parser_name=result.parser_name,
            confidence=result.confidence,
            user_id=user_id,
        )
        await self.email_updater.update(
            email_id=email.id, status=EmailParsedStatusValue.PARSED, failure_reason=None
        )
        summary.parsed += 1
        return event

    async def _invoke_llm(self, email: PendingEmail) -> ParseResult:
        try:
            return await self.llm_parser.parse(email)
        except Exception as exc:
            logger.exception("LLM 폴백 파서 예외")
            return ParseResult.fail(parser_name="llm", reason=f"LLM 호출 실패: {exc}")
