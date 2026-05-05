"""``MerchantAlias.learned_from`` 의 허용 값 (PRD 2.1)."""

from __future__ import annotations

from enum import StrEnum


class LearnedFrom(StrEnum):
    MANUAL = "manual"
    MATCHED = "matched"
    LLM = "llm"
    YAML = "yaml"
