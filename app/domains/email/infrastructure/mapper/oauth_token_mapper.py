from __future__ import annotations

from app.domains.email.domain.value_object.oauth_token import OAuthToken
from app.domains.email.infrastructure.orm.email_orm import OAuthTokenORM


def to_entity(
    orm: OAuthTokenORM, *, decrypt_access: bytes, decrypt_refresh: bytes | None
) -> OAuthToken:
    """ORM 행과 복호화된 토큰을 합쳐 Entity 생성. 복호화는 호출자(저장소)가 책임."""
    return OAuthToken(
        source=orm.source,
        account=orm.account,
        access_token=decrypt_access.decode("utf-8"),
        refresh_token=decrypt_refresh.decode("utf-8") if decrypt_refresh else None,
        expires_at=orm.expires_at,
        scopes=[s for s in orm.scopes.split(",") if s],
        user_id=orm.user_id,
    )
