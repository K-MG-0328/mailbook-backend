"""Gmail OAuth flow 시작. 외부 호출은 ``OAuthFlowProviderPort`` 로 추상화한다."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(slots=True)
class OAuthAuthorizationRequest:
    authorization_url: str
    state: str


class OAuthFlowProviderPort(ABC):
    @abstractmethod
    def build_authorization_url(self, *, state: str | None = None) -> OAuthAuthorizationRequest: ...

    @abstractmethod
    async def exchange_code_for_token(
        self, *, code: str, state: str | None
    ) -> "ExchangedToken": ...


@dataclass(slots=True)
class ExchangedToken:
    """Token 교환 결과 (account 식별자는 별도 user_info 호출로 채움)."""

    access_token: str
    refresh_token: str | None
    expires_at: object | None  # datetime — circular import 회피 목적의 약타입
    scopes: list[str]
    account_email: str  # token에 연결된 Gmail 주소


@dataclass(slots=True)
class StartOAuth:
    flow: OAuthFlowProviderPort

    async def execute(self) -> OAuthAuthorizationRequest:
        return self.flow.build_authorization_url()
