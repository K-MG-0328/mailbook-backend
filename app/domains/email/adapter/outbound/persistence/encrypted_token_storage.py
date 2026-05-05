"""Fernet 대칭 암호화 + DB 저장으로 ``OAuthTokenStoragePort`` 를 구현한다."""

from __future__ import annotations

from cryptography.fernet import Fernet
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exception.app_exception import AppException
from app.domains.email.application.port.oauth_token_storage_port import OAuthTokenStoragePort
from app.domains.email.domain.value_object.oauth_token import OAuthToken
from app.domains.email.infrastructure.orm.email_orm import OAuthTokenORM
from app.infrastructure.config.settings import get_settings


class EncryptedTokenStorage(OAuthTokenStoragePort):
    def __init__(self, session: AsyncSession):
        settings = get_settings()
        if not settings.token_encryption_key:
            raise AppException(
                status_code=500,
                message="TOKEN_ENCRYPTION_KEY 환경변수가 설정되지 않았습니다.",
            )
        self._fernet = Fernet(settings.token_encryption_key.encode())
        self._session = session

    async def save(self, token: OAuthToken) -> None:
        encrypted_access = self._fernet.encrypt(token.access_token.encode("utf-8"))
        encrypted_refresh = (
            self._fernet.encrypt(token.refresh_token.encode("utf-8"))
            if token.refresh_token
            else None
        )

        existing = await self._find_orm(source=token.source, account=token.account)
        if existing is None:
            orm = OAuthTokenORM(
                user_id=token.user_id,
                source=token.source,
                account=token.account,
                encrypted_access_token=encrypted_access,
                encrypted_refresh_token=encrypted_refresh,
                expires_at=token.expires_at,
                scopes=",".join(token.scopes),
            )
            self._session.add(orm)
        else:
            existing.user_id = token.user_id
            existing.encrypted_access_token = encrypted_access
            if encrypted_refresh is not None:
                existing.encrypted_refresh_token = encrypted_refresh
            existing.expires_at = token.expires_at
            existing.scopes = ",".join(token.scopes)
        await self._session.flush()

    async def load(self, *, source: str, account: str) -> OAuthToken | None:
        orm = await self._find_orm(source=source, account=account)
        if orm is None:
            return None
        access = self._fernet.decrypt(orm.encrypted_access_token).decode("utf-8")
        refresh = (
            self._fernet.decrypt(orm.encrypted_refresh_token).decode("utf-8")
            if orm.encrypted_refresh_token
            else None
        )
        return OAuthToken(
            source=orm.source,
            account=orm.account,
            access_token=access,
            refresh_token=refresh,
            expires_at=orm.expires_at,
            scopes=[s for s in orm.scopes.split(",") if s],
            user_id=orm.user_id,
        )

    async def list_accounts(self, *, source: str) -> list[str]:
        stmt = select(OAuthTokenORM.account).where(OAuthTokenORM.source == source)
        return list((await self._session.execute(stmt)).scalars().all())

    async def _find_orm(self, *, source: str, account: str) -> OAuthTokenORM | None:
        stmt = select(OAuthTokenORM).where(
            OAuthTokenORM.source == source, OAuthTokenORM.account == account
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()
