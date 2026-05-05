"""공용 Anthropic SDK 클라이언트 + 본문 sanitize 헬퍼.

도메인-특화 호출(파서 폴백, 매칭 disambiguation)은 각 도메인의 outbound adapter가
이 모듈의 ``get_anthropic_client``를 주입받아 사용한다.
"""

from __future__ import annotations

import re
from functools import lru_cache

from anthropic import AsyncAnthropic

from app.infrastructure.config.settings import get_settings

# 카드번호(13~19자리, 하이픈/공백 허용) → ****-****-****-1234 형태로 마스킹
_CARD_NUMBER_PATTERN = re.compile(r"\b(?:\d[\s-]?){12,18}\d\b")
# 주민등록번호 6-7
_RRN_PATTERN = re.compile(r"\b\d{6}[-\s]?[1-4]\d{6}\b")


@lru_cache
def get_anthropic_client() -> AsyncAnthropic:
    settings = get_settings()
    return AsyncAnthropic(api_key=settings.anthropic_api_key)


def sanitize_for_llm(text: str) -> str:
    """LLM에 전송하기 전 본문에서 민감정보를 마스킹한다 (PRD 4.2)."""
    if not text:
        return text
    masked = _CARD_NUMBER_PATTERN.sub(_mask_card_number, text)
    masked = _RRN_PATTERN.sub("******-*******", masked)
    return masked


def _mask_card_number(match: re.Match[str]) -> str:
    digits = re.sub(r"\D", "", match.group(0))
    if len(digits) < 4:
        return match.group(0)
    return f"****-****-****-{digits[-4:]}"
