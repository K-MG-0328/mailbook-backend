"""OAuth 토큰의 도메인 표현. 암호화/저장은 Infrastructure 책임."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class OAuthToken:
    source: str
    account: str
    access_token: str
    refresh_token: str | None = None
    expires_at: datetime | None = None
    scopes: list[str] = field(default_factory=list)
    user_id: int | None = None
