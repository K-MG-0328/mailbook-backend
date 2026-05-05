from __future__ import annotations

from rapidfuzz import fuzz

from app.domains.transaction.application.port.fuzzy_matcher_port import FuzzyMatcherPort


class RapidFuzzMatcher(FuzzyMatcherPort):
    def partial_ratio(self, a: str, b: str) -> int:
        return int(fuzz.partial_ratio(a, b))
