"""매칭 엔진 — PRD 2.2 Step 1~3 알고리즘 (Step 4 단독 처리는 별도 usecase).

순수 함수. 후보 PaymentEvent 목록을 받아 ``MatchDecision`` 을 반환.
LLM/fuzzy 호출은 Application Layer 가 콜백/포트로 주입.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from app.domains.transaction.domain.value_object.match_decision import MatchDecision

# PRD 2.2 고정 파라미터
TIME_WINDOW_MINUTES = 10
FUZZY_THRESHOLD = 60
LLM_FUZZY_THRESHOLD = 80  # LLM 호출 트리거: 후보 ≥ 2 AND fuzzy < 80


class CandidateEvent(Protocol):
    id: int
    merchant_name: str
    amount: int
    card_last4: str | None
    card_company: str | None


class FuzzyMatcher(Protocol):
    def partial_ratio(self, a: str, b: str) -> int: ...


class LlmDisambiguator(Protocol):
    """후보가 여러 개일 때 LLM 으로 매칭 여부를 판단."""

    async def pick(
        self, *, source: CandidateEvent, candidates: Sequence[CandidateEvent]
    ) -> int | None:
        """선택된 candidate 의 id 반환. 매칭 불가는 None."""


@dataclass(slots=True)
class MatchingEngine:
    """``find_match`` 만 실행. 캐시/저장은 호출자 책임."""

    fuzzy: FuzzyMatcher

    def disambiguate_sync(
        self,
        source: CandidateEvent,
        candidates: Sequence[CandidateEvent],
    ) -> tuple[MatchDecision, bool]:
        """LLM 호출 없이 sync 분기 결정. 두 번째 반환값은 'LLM 호출이 필요한가'.

        반환:
            (MatchDecision, needs_llm)
            - needs_llm=True 인 경우 호출자가 LLM 호출 후 ``finalize_with_llm`` 호출.
        """
        if not candidates:
            return MatchDecision.no_match(), False
        if len(candidates) == 1:
            return MatchDecision.matched(candidates[0].id, confidence=0.95), False

        # Step 3a: card_last4 일치로 좁히기
        if source.card_last4:
            narrowed = [c for c in candidates if c.card_last4 == source.card_last4]
            if len(narrowed) == 1:
                return MatchDecision.matched(narrowed[0].id, confidence=0.93), False
            if len(narrowed) > 1:
                candidates = narrowed

        # Step 3b: 가맹점명 fuzzy match (FUZZY_THRESHOLD 60 이상만 후보 유지)
        scored = [
            (c, self.fuzzy.partial_ratio(_norm(source.merchant_name), _norm(c.merchant_name)))
            for c in candidates
        ]
        passing = [(c, s) for c, s in scored if s >= FUZZY_THRESHOLD]
        if len(passing) == 1:
            chosen, score = passing[0]
            return (
                MatchDecision.matched(chosen.id, confidence=min(0.9, score / 100.0 + 0.1)),
                False,
            )

        # Step 3c: LLM 폴백 트리거
        # PRD: 후보 ≥ 2 AND fuzzy < 80 → LLM. 위에서 passing 이 1개가 아니면 모두 80 미만
        # 또는 0/2+ 개. LLM 분기.
        return MatchDecision.no_match(), True

    def finalize_with_llm(
        self,
        source: CandidateEvent,
        candidates: Sequence[CandidateEvent],
        llm_choice: int | None,
    ) -> MatchDecision:
        """LLM 결과를 받아 최종 결정. None 이면 manual review."""
        if llm_choice is None:
            return MatchDecision.needs_review("후보 다수 + fuzzy/card_last4/LLM 모두 결정 불가")
        for c in candidates:
            if c.id == llm_choice:
                return MatchDecision.matched(llm_choice, confidence=0.7)
        return MatchDecision.needs_review("LLM 이 후보 외 id 반환")


def _norm(name: str) -> str:
    return (name or "").strip().casefold()
