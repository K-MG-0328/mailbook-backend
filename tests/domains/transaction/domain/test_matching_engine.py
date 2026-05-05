from dataclasses import dataclass

from app.domains.transaction.domain.service.matching_engine import (
    FUZZY_THRESHOLD,
    FuzzyMatcher,
    MatchingEngine,
)


@dataclass
class _Event:
    id: int
    merchant_name: str
    amount: int
    card_last4: str | None
    card_company: str | None


class _DefaultFuzzy(FuzzyMatcher):
    """이름이 같으면 100, 부분일치는 70, 그 외 30."""

    def partial_ratio(self, a: str, b: str) -> int:
        if a == b:
            return 100
        if a in b or b in a:
            return 70
        return 30


def _engine() -> MatchingEngine:
    return MatchingEngine(fuzzy=_DefaultFuzzy())


def _ev(eid: int, merchant: str, last4: str | None) -> _Event:
    return _Event(id=eid, merchant_name=merchant, amount=10000, card_last4=last4, card_company=None)


def test_no_candidates_returns_no_match() -> None:
    decision, needs_llm = _engine().disambiguate_sync(_ev(1, "쿠팡", None), [])
    assert decision.counterpart_event_id is None
    assert not needs_llm


def test_single_candidate_matches_with_high_confidence() -> None:
    src = _ev(1, "쿠팡", None)
    cand = _ev(2, "쿠팡결제", None)
    decision, needs_llm = _engine().disambiguate_sync(src, [cand])
    assert decision.counterpart_event_id == 2
    assert decision.confidence == 0.95
    assert not needs_llm


def test_two_candidates_card_last4_disambiguation() -> None:
    src = _ev(1, "쿠팡", "1234")
    cands = [_ev(2, "쿠팡결제", "9999"), _ev(3, "쿠팡결제", "1234")]
    decision, needs_llm = _engine().disambiguate_sync(src, cands)
    assert decision.counterpart_event_id == 3
    assert not needs_llm


def test_two_candidates_fuzzy_disambiguation_when_one_passes_threshold() -> None:
    src = _ev(1, "쿠팡", None)
    # 부분일치(70 ≥ 60) 1개, 무관(30 < 60) 1개
    cands = [_ev(2, "쿠팡결제", None), _ev(3, "스타벅스", None)]
    decision, needs_llm = _engine().disambiguate_sync(src, cands)
    assert decision.counterpart_event_id == 2
    assert not needs_llm


def test_two_candidates_with_two_fuzzy_passes_triggers_llm() -> None:
    src = _ev(1, "쿠팡", None)
    cands = [_ev(2, "쿠팡결제", None), _ev(3, "쿠팡결제2", None)]
    # 두 후보 모두 부분일치(70) — passing 1개가 아니어서 LLM 분기
    decision, needs_llm = _engine().disambiguate_sync(src, cands)
    assert decision.counterpart_event_id is None
    assert needs_llm


def test_two_candidates_all_below_fuzzy_threshold_triggers_llm() -> None:
    src = _ev(1, "쿠팡", None)
    cands = [_ev(2, "스타벅스", None), _ev(3, "넷플릭스", None)]
    decision, needs_llm = _engine().disambiguate_sync(src, cands)
    assert decision.counterpart_event_id is None
    assert needs_llm


def test_finalize_with_llm_returns_matched_when_choice_is_valid() -> None:
    src = _ev(1, "쿠팡", None)
    cands = [_ev(2, "쿠팡A", None), _ev(3, "쿠팡B", None)]
    decision = _engine().finalize_with_llm(src, cands, llm_choice=3)
    assert decision.counterpart_event_id == 3
    assert decision.confidence == 0.7


def test_finalize_with_llm_returns_review_when_none() -> None:
    src = _ev(1, "쿠팡", None)
    decision = _engine().finalize_with_llm(src, [_ev(2, "x", None)], llm_choice=None)
    assert decision.requires_manual_review
    assert decision.counterpart_event_id is None


def test_finalize_with_llm_returns_review_when_invalid_id() -> None:
    src = _ev(1, "쿠팡", None)
    decision = _engine().finalize_with_llm(src, [_ev(2, "x", None)], llm_choice=999)
    assert decision.requires_manual_review


def test_card_last4_priority_over_fuzzy_when_unique_match() -> None:
    src = _ev(1, "스타벅스", "1234")
    # 가맹점명은 모두 다르지만 last4가 1개만 일치 — last4 우선
    cands = [_ev(2, "쿠팡", "1234"), _ev(3, "넷플릭스", "9999")]
    decision, needs_llm = _engine().disambiguate_sync(src, cands)
    assert decision.counterpart_event_id == 2
    assert not needs_llm


def test_fuzzy_threshold_constant_value() -> None:
    # PRD 2.2: FUZZY_THRESHOLD 는 60 으로 고정
    assert FUZZY_THRESHOLD == 60
