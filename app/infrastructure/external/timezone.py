"""KST 시간대 헬퍼.

PRD 2.4: ParseResult.paid_at 은 KST timezone-aware 이어야 한다.
PRD 7: 시간대 혼재 시 본문 시각 우선, 본문에 없으면 헤더를 KST로 변환.
"""

from __future__ import annotations

from datetime import datetime, timezone
from functools import lru_cache
from zoneinfo import ZoneInfo

from app.infrastructure.config.settings import get_settings


@lru_cache
def get_app_tz() -> ZoneInfo:
    return ZoneInfo(get_settings().timezone)


def to_app_tz(dt: datetime) -> datetime:
    """naive 입력은 UTC로 간주한 후 앱 시간대(기본 KST)로 변환한다."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(get_app_tz())


def now_in_app_tz() -> datetime:
    return datetime.now(tz=get_app_tz())
