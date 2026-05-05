"""매칭 결과 — PRD 2.2 알고리즘의 출력."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class MatchDecision:
    counterpart_event_id: int | None
    confidence: float
    requires_manual_review: bool = False
    note: str | None = None

    @classmethod
    def matched(cls, counterpart_id: int, confidence: float) -> "MatchDecision":
        return cls(counterpart_event_id=counterpart_id, confidence=confidence)

    @classmethod
    def no_match(cls) -> "MatchDecision":
        return cls(counterpart_event_id=None, confidence=0.0)

    @classmethod
    def needs_review(cls, note: str) -> "MatchDecision":
        return cls(
            counterpart_event_id=None,
            confidence=0.0,
            requires_manual_review=True,
            note=note,
        )
