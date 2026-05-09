"""미매칭 PaymentEvent 들을 PRD 2.2 알고리즘으로 묶어 Transaction 생성.

흐름:
1. 미매칭 이벤트 목록 조회
2. 각 이벤트에 대해:
   a. 반대 타입 + 같은 amount + ±10분 후보 조회 (PRD 2.2 Step 1)
   b. MatchingEngine.disambiguate_sync (Step 2~3a/3b)
   c. needs_llm 이면 LlmDisambiguator.pick 후 finalize_with_llm
   d. matched 면 Transaction 생성 + 두 이벤트의 transaction_id 갱신
   e. needs_review 면 Transaction(requires_manual_review=True)
3. 처리 결과 카운트 반환
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from app.domains.transaction.application.port.fuzzy_matcher_port import FuzzyMatcherPort
from app.domains.transaction.application.port.llm_disambiguator_port import LlmDisambiguatorPort
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
from app.domains.transaction.domain.service.matching_engine import (
    TIME_WINDOW_MINUTES,
    MatchingEngine,
)
from app.domains.transaction.domain.value_object.payment_method import PaymentMethod

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class MatchSummary:
    matched: int
    review_required: int
    skipped: int  # 후보 0 — solo 처리는 별도 usecase


@dataclass(slots=True)
class MatchUnmatchedEvents:
    payment_events: PaymentEventQueryPort
    transactions: TransactionRepositoryPort
    fuzzy: FuzzyMatcherPort
    llm: LlmDisambiguatorPort
    merchant_resolver: MerchantResolverPort
    classifier: Classifier

    async def execute(self, *, user_id: int | None, limit: int = 200) -> MatchSummary:
        engine = MatchingEngine(fuzzy=self.fuzzy)
        summary = MatchSummary(matched=0, review_required=0, skipped=0)

        unmatched = await self.payment_events.list_unmatched(user_id=user_id, limit=limit)
        # transaction_id 가 채워진 건 건너뛰기 위해 in-memory set
        consumed: set[int] = set()

        for source in unmatched:
            if source.id in consumed:
                continue

            opposite = _opposite(source.event_type)
            candidates = await self.payment_events.find_candidates(
                opposite_event_type=opposite,
                amount=source.amount,
                center=source.paid_at,
                window_minutes=TIME_WINDOW_MINUTES,
                user_id=user_id,
            )
            # 이미 매칭된 후보 제외 (DB 단계에서 제외되지만 in-memory set 에 의해 안전)
            candidates = [c for c in candidates if c.id not in consumed]

            decision, needs_llm = engine.disambiguate_sync(source, candidates)
            if needs_llm:
                pick = await self.llm.pick(source=source, candidates=candidates)
                decision = engine.finalize_with_llm(source, candidates, pick)

            if decision.counterpart_event_id is not None:
                txn = await self._create_transaction(
                    source=source,
                    counterpart_id=decision.counterpart_event_id,
                    candidates=candidates,
                    confidence=decision.confidence,
                    user_id=user_id,
                )
                await self.payment_events.assign_transaction(
                    event_ids=[source.id, decision.counterpart_event_id],
                    transaction_id=_require_id(txn),
                )
                consumed.add(source.id)
                consumed.add(decision.counterpart_event_id)
                summary.matched += 1
            elif decision.requires_manual_review:
                txn = await self._create_review_transaction(
                    source=source, note=decision.note, user_id=user_id
                )
                await self.payment_events.assign_transaction(
                    event_ids=[source.id], transaction_id=_require_id(txn)
                )
                consumed.add(source.id)
                summary.review_required += 1
            else:
                summary.skipped += 1

        return summary

    async def _create_transaction(
        self,
        *,
        source: CandidateEventDto,
        counterpart_id: int,
        candidates: list[CandidateEventDto],
        confidence: float,
        user_id: int | None,
    ) -> Transaction:
        counterpart = next(c for c in candidates if c.id == counterpart_id)
        merchant_event, card_event = (
            (source, counterpart)
            if source.event_type == "merchant_receipt"
            else (counterpart, source)
        )
        canonical = await self.merchant_resolver.resolve(
            raw_name=merchant_event.merchant_name, user_id=user_id
        )
        category = self.classifier.pick(alias_category=canonical.category if canonical else None)
        txn = Transaction(
            merchant_name=merchant_event.merchant_name,
            canonical_merchant=canonical.canonical if canonical else None,
            amount=source.amount,
            currency=source.currency,
            paid_at=source.paid_at,
            payment_method=PaymentMethod.CARD,
            category=category or None,
            card_company=card_event.card_company,
            card_last4=card_event.card_last4,
            note=f"매칭 신뢰도 {confidence:.2f}",
            user_id=user_id,
        )
        return await self.transactions.save(txn)

    async def _create_review_transaction(
        self,
        *,
        source: CandidateEventDto,
        note: str | None,
        user_id: int | None,
    ) -> Transaction:
        canonical = await self.merchant_resolver.resolve(
            raw_name=source.merchant_name, user_id=user_id
        )
        txn = Transaction(
            merchant_name=source.merchant_name,
            canonical_merchant=canonical.canonical if canonical else None,
            amount=source.amount,
            currency=source.currency,
            paid_at=source.paid_at,
            payment_method=PaymentMethod.UNKNOWN,
            category=self.classifier.pick(alias_category=canonical.category if canonical else None)
            or None,
            card_company=source.card_company,
            card_last4=source.card_last4,
            note=note,
            requires_manual_review=True,
            user_id=user_id,
        )
        return await self.transactions.save(txn)


def _opposite(event_type: str) -> str:
    return "card_notification" if event_type == "merchant_receipt" else "merchant_receipt"


def _require_id(txn: Transaction) -> int:
    if txn.id is None:
        raise ValueError("저장 직후 Transaction.id 가 없습니다.")
    return txn.id
