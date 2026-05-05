"""raw 가맹점명 → canonical 변환 도메인 서비스.

순수 함수 — 정규화 규칙(공백/케이스/구두점)만 적용한다.
실제 alias DB 조회는 Application Layer 의 ``ResolveCanonical`` UseCase가 담당.
"""

from __future__ import annotations

import re

_WHITESPACE_RE = re.compile(r"\s+")
# (주), (유), 주식회사 등 한국 법인 표기 제거
_KOREAN_CORP_RE = re.compile(r"\(\s*[주유]\s*\)|주식회사|유한회사")
# PG/결제대행 prefix (국내 흔한 경우)
_PG_PREFIXES = ("KCP_", "KCP-", "INICIS_", "TOSS_", "NHN_")


def normalize_raw_name(raw: str) -> str:
    """비교 가능한 정규화 키. 매칭 / 알리아스 lookup의 입력으로 사용."""
    if not raw:
        return ""

    normalized = raw.strip()
    normalized = _KOREAN_CORP_RE.sub("", normalized)
    for prefix in _PG_PREFIXES:
        if normalized.upper().startswith(prefix):
            normalized = normalized[len(prefix) :]
    normalized = _WHITESPACE_RE.sub(" ", normalized).strip()
    return normalized.casefold()
