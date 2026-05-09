from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta

import pytest

from app.domains.transaction.application.port.merchant_resolver_port import (
    CanonicalMerchantDto,
    MerchantResolverPort,
)
from app.domains.transaction.application.port.payment_event_query_port import (
    CandidateEventDto,
    PaymentEventQueryPort,
)
from app.domains.transaction.application.port.transaction_repository_port import (
    TransactionRepositoryPort,
)
from app.domains.transaction.application.usecase.resolve_solo_transactions import (
    SOLO_TIMEOUT_HOURS,
    ResolveSoloTransactions,
)
from app.domains.transaction.domain.entity.transaction import Transaction
from app.domains.transaction.domain.service.classifier import Classifier
from app.infrastructure.external.timezone import now_in_app_tz


class _AlwaysValid:
    def is_valid(self, name: str) -> bool:
        return True


class _FakePaymentEvents(PaymentEventQueryPort):
    def __init__(self, events: list[CandidateEventDto]) -> None:
        self._events = events
        self.assigned: list[tuple[list[int], int]] = []

    async def list_unmatched(self, *, user_id: int | None, limit: int) -> list[CandidateEventDto]:
        return [e for e in self._events if e.transaction_id is None][:limit]

    async def find_candidates(
        self,
        *,
        opposite_event_type: str,
        amount: int,
        center: datetime,
        window_minutes: int,
        user_id: int | None,
    ) -> list[CandidateEventDto]:
        return []

    async def list_unmatched_older_than(
        self, *, before: datetime, user_id: int | None, limit: int
    ) -> list[CandidateEventDto]:
        return [e for e in self._events if e.transaction_id is None and e.paid_at <= before][:limit]

    async def assign_transaction(self, *, event_ids: list[int], transaction_id: int) -> None:
        self.assigned.append((event_ids, transaction_id))
        for event in self._events:
            if event.id in event_ids:
                idx = self._events.index(event)
                self._events[idx] = replace(event, transaction_id=transaction_id)


class _FakeTransactions(TransactionRepositoryPort):
    def __init__(self) -> None:
        self.saved: list[Transaction] = []
        self._next_id = 1

    async def save(self, transaction: Transaction) -> Transaction:
        transaction.id = self._next_id
        self._next_id += 1
        self.saved.append(transaction)
        return transaction

    async def get(self, transaction_id: int) -> Transaction | None:
        return next((t for t in self.saved if t.id == transaction_id), None)

    async def list_recent(
        self, *, user_id: int | None, limit: int, offset: int
    ) -> list[Transaction]:
        return list(self.saved)

    async def list_review_required(
        self, *, user_id: int | None, limit: int, offset: int
    ) -> list[Transaction]:
        return []

    async def list_in_period(
        self, *, user_id: int | None, start: datetime, end: datetime
    ) -> list[Transaction]:
        return []

    async def update_verified(
        self, *, transaction_id: int, is_verified: bool, note: str | None
    ) -> Transaction | None:
        return None


class _FakeMerchantResolver(MerchantResolverPort):
    async def resolve(self, *, raw_name: str, user_id: int | None) -> CanonicalMerchantDto | None:
        return CanonicalMerchantDto(canonical=raw_name, category="기타")


def _event(
    eid: int,
    *,
    event_type: str = "merchant_receipt",
    paid_at: datetime,
    merchant: str = "Trancy",
    amount: int = 4800,
    currency: str = "KRW",
) -> CandidateEventDto:
    return CandidateEventDto(
        id=eid,
        event_type=event_type,
        merchant_name=merchant,
        amount=amount,
        currency=currency,
        paid_at=paid_at,
        card_company=None,
        card_last4=None,
        transaction_id=None,
        user_id=None,
    )


def _make_usecase(
    events: list[CandidateEventDto],
) -> tuple[ResolveSoloTransactions, _FakePaymentEvents, _FakeTransactions]:
    payment_events = _FakePaymentEvents(events)
    transactions = _FakeTransactions()
    usecase = ResolveSoloTransactions(
        payment_events=payment_events,
        transactions=transactions,
        merchant_resolver=_FakeMerchantResolver(),
        classifier=Classifier(validator=_AlwaysValid()),
    )
    return usecase, payment_events, transactions


@pytest.mark.asyncio
async def test_force_processes_recent_events() -> None:
    recent = _event(1, paid_at=now_in_app_tz())
    usecase, payment_events, transactions = _make_usecase([recent])

    summary = await usecase.execute(user_id=None, force=True)

    assert summary.non_card == 1
    assert summary.subscription == 0
    assert len(transactions.saved) == 1
    assert transactions.saved[0].merchant_name == "Trancy"
    assert payment_events.assigned == [([1], 1)]


@pytest.mark.asyncio
async def test_default_skips_recent_events() -> None:
    recent = _event(1, paid_at=now_in_app_tz())
    usecase, _payment_events, transactions = _make_usecase([recent])

    summary = await usecase.execute(user_id=None)

    assert summary.subscription == 0
    assert summary.non_card == 0
    assert transactions.saved == []


@pytest.mark.asyncio
async def test_force_handles_card_and_merchant() -> None:
    now = now_in_app_tz()
    aged = now - timedelta(hours=SOLO_TIMEOUT_HOURS + 1)
    events = [
        _event(1, event_type="merchant_receipt", paid_at=now, merchant="Trancy"),
        _event(2, event_type="card_notification", paid_at=aged, merchant="신한카드"),
    ]
    usecase, _payment_events, transactions = _make_usecase(events)

    summary = await usecase.execute(user_id=None, force=True)

    assert summary.non_card == 1
    assert summary.subscription == 1
    assert len(transactions.saved) == 2
