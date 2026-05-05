"""24시간 timeout 처리 (PRD 2.2 Step 4).

card_notification 단독 → 정기결제 추정. merchant_receipt 단독 → 카드 외 결제 추정.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from app.domains.transaction.application.port.merchant_resolver_port import MerchantResolverPort
from app.domains.transaction.application.port.payment_event_query_port import (
    CandidateEventDto,
    PaymentEventQueryPort,
)
from app.domains.transaction.application.port.transaction_repository_port import (
    TransactionRepositoryPort,
)
from app.domains.transaction.domain.entity.transaction import Transaction
from app.domains.transaction.domain.service.classifier import Classifier
from app.domains.transaction.domain.value_object.payment_method import PaymentMethod
from app.infrastructure.external.timezone import now_in_app_tz

SOLO_TIMEOUT_HOURS = 24


@dataclass(slots=True)
class SoloSummary:
    subscription: int  # card_notification 단독
    non_card: int  # merchant_receipt 단독


@dataclass(slots=True)
class ResolveSoloTransactions:
    payment_events: PaymentEventQueryPort
    transactions: TransactionRepositoryPort
    merchant_resolver: MerchantResolverPort
    classifier: Classifier

    async def execute(
        self, *, user_id: int | None, limit: int = 200, force: bool = False
    ) -> SoloSummary:
        if force:
            events = await self.payment_events.list_unmatched(user_id=user_id, limit=limit)
        else:
            cutoff = now_in_app_tz() - timedelta(hours=SOLO_TIMEOUT_HOURS)
            events = await self.payment_events.list_unmatched_older_than(
                before=cutoff, user_id=user_id, limit=limit
            )
        summary = SoloSummary(subscription=0, non_card=0)
        for event in events:
            txn = await self._create_solo(event=event, user_id=user_id)
            await self.payment_events.assign_transaction(
                event_ids=[event.id], transaction_id=_require_id(txn)
            )
            if event.event_type == "card_notification":
                summary.subscription += 1
            else:
                summary.non_card += 1
        return summary

    async def _create_solo(self, *, event: CandidateEventDto, user_id: int | None) -> Transaction:
        canonical = await self.merchant_resolver.resolve(
            raw_name=event.merchant_name, user_id=user_id
        )
        if event.event_type == "card_notification":
            payment_method = PaymentMethod.SUBSCRIPTION
            note = "24h 후 단독 — 정기결제로 추정"
        else:
            payment_method = PaymentMethod.NON_CARD
            note = "24h 후 단독 — 카드 외 결제(계좌이체 등) 추정"
        txn = Transaction(
            merchant_name=event.merchant_name,
            canonical_merchant=canonical.canonical if canonical else None,
            amount=event.amount,
            paid_at=event.paid_at,
            payment_method=payment_method,
            category=self.classifier.pick(alias_category=canonical.category if canonical else None)
            or None,
            card_company=event.card_company,
            card_last4=event.card_last4,
            note=note,
            user_id=user_id,
        )
        return await self.transactions.save(txn)


def _require_id(txn: Transaction) -> int:
    if txn.id is None:
        raise ValueError("저장 직후 Transaction.id 가 없습니다.")
    return txn.id
