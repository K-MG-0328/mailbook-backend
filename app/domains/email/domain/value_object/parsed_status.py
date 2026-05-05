from __future__ import annotations

from enum import StrEnum


class ParsedStatus(StrEnum):
    PENDING = "pending"
    PARSED = "parsed"
    SKIPPED = "skipped"
    FAILED = "failed"
