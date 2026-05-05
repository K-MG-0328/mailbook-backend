"""``Parser`` 추상 베이스 (PRD 2.4 인터페이스 계약).

도메인 순수 코드 — Domain은 Email Entity의 정확한 위치를 모르고 단순히 EmailLike
프로토콜만 받는다 (도메인 간 결합 회피).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Protocol

from app.domains.payment_event.domain.value_object.parse_result import ParseResult


class EmailLike(Protocol):
    """Parser 가 필요로 하는 이메일 표면 — 다른 도메인 entity 의 의존을 피한다."""

    sender: str
    subject: str
    body_text: str
    body_html: str
    received_at: datetime


class Parser(ABC):
    name: str  # 파서 식별자
    sender_patterns: list[str]  # 매칭할 발신자 도메인/주소 (정규식 OR 부분일치)
    subject_patterns: list[str]  # 매칭할 제목 키워드

    @abstractmethod
    def can_parse(self, email: EmailLike) -> bool: ...

    @abstractmethod
    def parse(self, email: EmailLike) -> ParseResult: ...
