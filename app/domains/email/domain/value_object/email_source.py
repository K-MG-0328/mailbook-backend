from __future__ import annotations

from enum import StrEnum


class EmailSource(StrEnum):
    GMAIL = "gmail"
    NAVER = "naver"
    DAUM = "daum"
