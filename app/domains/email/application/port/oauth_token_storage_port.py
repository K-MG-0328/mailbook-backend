from __future__ import annotations

from abc import ABC, abstractmethod

from app.domains.email.domain.value_object.oauth_token import OAuthToken


class OAuthTokenStoragePort(ABC):
    @abstractmethod
    async def save(self, token: OAuthToken) -> None:
        """``(source, account)`` upsert. access/refresh 토큰은 저장 시점에 암호화한다."""

    @abstractmethod
    async def load(self, *, source: str, account: str) -> OAuthToken | None: ...

    @abstractmethod
    async def list_accounts(self, *, source: str) -> list[str]: ...
