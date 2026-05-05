from __future__ import annotations

from abc import ABC, abstractmethod


class FuzzyMatcherPort(ABC):
    @abstractmethod
    def partial_ratio(self, a: str, b: str) -> int: ...
