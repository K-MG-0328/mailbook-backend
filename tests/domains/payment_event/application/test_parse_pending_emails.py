from datetime import datetime, timezone

import pytest

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
from app.domains.payment_event.application.usecase.parse_pending_emails import ParsePendingEmails
from app.domains.payment_event.domain.entity.payment_event import PaymentEvent
from app.domains.payment_event.domain.service.parser import EmailLike, Parser
from app.domains.payment_event.domain.value_object.event_type import EventType
from app.domains.payment_event.domain.value_object.parse_result import ParseResult


class _StubEmailQuery(EmailQueryPort):
    def __init__(self, emails: list[PendingEmail]):
        self._emails = emails

    async def list_pending(self, *, user_id, limit):  # type: ignore[no-untyped-def]
        return self._emails

    async def get_by_id(self, *, email_id):  # type: ignore[no-untyped-def]
        return None


class _RecordingUpdater(EmailStatusUpdaterPort):
    def __init__(self) -> None:
        self.updates: list[tuple[int, EmailParsedStatusValue, str | None]] = []

    async def update(self, *, email_id, status, failure_reason):  # type: ignore[no-untyped-def]
        self.updates.append((email_id, status, failure_reason))


class _RecordingRepo(PaymentEventRepositoryPort):
    def __init__(self) -> None:
        self.saved: list[PaymentEvent] = []

    async def save(self, event):  # type: ignore[no-untyped-def]
        self.saved.append(event)
        return event

    async def find_by_email_id(self, email_id):  # type: ignore[no-untyped-def]
        return None

    async def list_unmatched_in_window(self, **kwargs):  # type: ignore[no-untyped-def]
        return []

    async def list_unmatched_older_than(self, **kwargs):  # type: ignore[no-untyped-def]
        return []

    async def list_recent(self, **kwargs):  # type: ignore[no-untyped-def]
        return []

    async def assign_transaction(self, **kwargs):  # type: ignore[no-untyped-def]
        return None


class _ProviderWith(ParserProviderPort):
    def __init__(self, parsers: list[Parser]):
        self._parsers = parsers

    def list_parsers(self):  # type: ignore[no-untyped-def]
        return list(self._parsers)


class _LlmStub(LlmParserPort):
    def __init__(self, result: ParseResult):
        self.result = result
        self.invocations = 0

    async def parse(self, email):  # type: ignore[no-untyped-def]
        self.invocations += 1
        return self.result


class _AcceptingParser(Parser):
    name = "stub_card"
    sender_patterns = ["card.com"]
    subject_patterns: list[str] = []

    def __init__(self, result: ParseResult):
        self._result = result

    def can_parse(self, email: EmailLike) -> bool:
        return "card.com" in email.sender

    def parse(self, email: EmailLike) -> ParseResult:
        return self._result


def _now_kst() -> datetime:
    return datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc)


def _email(eid: int, *, sender: str = "x@unknown.com", body: str = "결제 완료") -> PendingEmail:
    return PendingEmail(
        id=eid,
        sender=sender,
        subject="테스트",
        body_text=body,
        body_html="",
        received_at=_now_kst(),
    )


@pytest.mark.asyncio
async def test_skipped_when_body_empty() -> None:
    updater = _RecordingUpdater()
    usecase = ParsePendingEmails(
        email_query=_StubEmailQuery([_email(1, body="")]),
        email_updater=updater,
        parser_provider=_ProviderWith([]),
        payment_event_repo=_RecordingRepo(),
        llm_parser=_LlmStub(ParseResult.fail(parser_name="llm", reason="x")),
    )
    summary = await usecase.execute(user_id=1, limit=10)
    assert summary.skipped == 1
    assert updater.updates == [(1, EmailParsedStatusValue.SKIPPED, updater.updates[0][2])]
    assert "본문이 비어" in (updater.updates[0][2] or "")


@pytest.mark.asyncio
async def test_parsed_via_rule_based_parser() -> None:
    success_result = ParseResult(
        success=True,
        parser_name="stub_card",
        event_type=EventType.CARD_NOTIFICATION,
        merchant_name="쿠팡",
        amount=32500,
        paid_at=_now_kst(),
        card_company="신한카드",
        card_last4="1234",
        confidence=0.9,
    )
    repo = _RecordingRepo()
    updater = _RecordingUpdater()
    llm = _LlmStub(ParseResult.fail(parser_name="llm", reason="x"))
    usecase = ParsePendingEmails(
        email_query=_StubEmailQuery([_email(7, sender="noreply@card.com", body="결제")]),
        email_updater=updater,
        parser_provider=_ProviderWith([_AcceptingParser(success_result)]),
        payment_event_repo=repo,
        llm_parser=llm,
    )
    summary = await usecase.execute(user_id=42, limit=10)
    assert summary.parsed == 1
    assert summary.llm_invoked == 0
    assert llm.invocations == 0
    assert len(repo.saved) == 1
    assert repo.saved[0].merchant_name == "쿠팡"
    assert repo.saved[0].user_id == 42
    assert updater.updates == [(7, EmailParsedStatusValue.PARSED, None)]


@pytest.mark.asyncio
async def test_llm_fallback_when_no_parser_matches() -> None:
    llm_result = ParseResult(
        success=True,
        parser_name="anthropic_llm_fallback",
        event_type=EventType.MERCHANT_RECEIPT,
        merchant_name="카카오T",
        amount=4500,
        paid_at=_now_kst(),
        confidence=0.7,
    )
    repo = _RecordingRepo()
    updater = _RecordingUpdater()
    llm = _LlmStub(llm_result)
    usecase = ParsePendingEmails(
        email_query=_StubEmailQuery([_email(2, sender="noreply@unknown.com", body="영수증")]),
        email_updater=updater,
        parser_provider=_ProviderWith([]),
        payment_event_repo=repo,
        llm_parser=llm,
    )
    summary = await usecase.execute(user_id=1, limit=10)
    assert summary.parsed == 1
    assert summary.llm_invoked == 1
    assert llm.invocations == 1
    assert repo.saved[0].parser_name == "anthropic_llm_fallback"


@pytest.mark.asyncio
async def test_failed_after_rule_and_llm_both_fail() -> None:
    rule_fail = ParseResult.fail(parser_name="stub_card", reason="amount 누락")
    llm_fail = ParseResult.fail(parser_name="llm", reason="응답 부정확")
    repo = _RecordingRepo()
    updater = _RecordingUpdater()
    llm = _LlmStub(llm_fail)
    usecase = ParsePendingEmails(
        email_query=_StubEmailQuery([_email(9, sender="noreply@card.com", body="?")]),
        email_updater=updater,
        parser_provider=_ProviderWith([_AcceptingParser(rule_fail)]),
        payment_event_repo=repo,
        llm_parser=llm,
    )
    summary = await usecase.execute(user_id=1, limit=10)
    assert summary.failed == 1
    assert summary.llm_invoked == 1
    assert len(repo.saved) == 0
    # email 상태가 FAILED 로 마킹되었는지
    assert updater.updates[0][1] == EmailParsedStatusValue.FAILED
