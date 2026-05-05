"""Google OAuth 2.0 Flow + UserInfo 조회 — ``OAuthFlowProviderPort`` 구현."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from app.common.exception.app_exception import AppException
from app.domains.email.application.usecase.start_oauth import (
    ExchangedToken,
    OAuthAuthorizationRequest,
    OAuthFlowProviderPort,
)
from app.infrastructure.config.settings import get_settings

# Gmail 읽기 + 라벨 적용 + 사용자 이메일 식별
GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.labels",
    "https://www.googleapis.com/auth/gmail.modify",
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
]


class GoogleOAuthFlow(OAuthFlowProviderPort):
    def __init__(self) -> None:
        settings = get_settings()
        if not (settings.gmail_oauth_client_id and settings.gmail_oauth_client_secret):
            raise AppException(
                status_code=500,
                message="GMAIL_OAUTH_CLIENT_ID / SECRET 환경변수가 설정되지 않았습니다.",
            )
        self._client_id = settings.gmail_oauth_client_id
        self._client_secret = settings.gmail_oauth_client_secret
        self._redirect_uri = settings.gmail_oauth_redirect_uri

    def _build_flow(self, state: str | None = None) -> Flow:
        client_config = {
            "web": {
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [self._redirect_uri],
            }
        }
        flow = Flow.from_client_config(client_config, scopes=GMAIL_SCOPES, state=state)
        flow.redirect_uri = self._redirect_uri
        # confidential web client (client_secret 보유) 라 PKCE 미사용. start/callback 사이
        # code_verifier 보존이 필요해지는 걸 회피.
        flow.autogenerate_code_verifier = False
        flow.code_verifier = None
        return flow

    def build_authorization_url(self, *, state: str | None = None) -> OAuthAuthorizationRequest:
        flow = self._build_flow(state=state)
        url, generated_state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
        )
        return OAuthAuthorizationRequest(authorization_url=url, state=generated_state)

    async def exchange_code_for_token(self, *, code: str, state: str | None) -> ExchangedToken:
        flow = self._build_flow(state=state)
        await asyncio.to_thread(flow.fetch_token, code=code)
        creds = flow.credentials
        # account 식별: userinfo.email
        account_email = await asyncio.to_thread(_fetch_user_email, creds)
        expires_at: datetime | None = None
        if creds.expiry is not None:
            # google-auth는 naive UTC로 expiry를 반환
            expires_at = creds.expiry.replace(tzinfo=timezone.utc)
        return ExchangedToken(
            access_token=creds.token,
            refresh_token=creds.refresh_token,
            expires_at=expires_at,
            scopes=list(creds.scopes or []),
            account_email=account_email,
        )


def _fetch_user_email(creds: object) -> str:
    """google-api-python-client 의 ``oauth2`` discovery로 이메일을 조회한다."""
    service = build("oauth2", "v2", credentials=creds, cache_discovery=False)
    info = service.userinfo().get().execute()
    email = info.get("email")
    if not email:
        raise AppException(status_code=502, message="Google userinfo 응답에 email이 없습니다.")
    return str(email)
