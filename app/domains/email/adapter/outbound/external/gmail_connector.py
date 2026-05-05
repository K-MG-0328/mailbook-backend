"""Gmail API 기반 ``EmailConnectorPort`` 구현.

google-api-python-client 가 동기 라이브러리이므로 ``asyncio.to_thread`` 로 감싼다.
"""

from __future__ import annotations

import asyncio
import base64
import logging
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from email.utils import parseaddr, parsedate_to_datetime
from typing import Any

from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app.common.exception.app_exception import AppException
from app.domains.email.application.port.email_connector_port import EmailConnectorPort
from app.domains.email.application.port.oauth_token_storage_port import OAuthTokenStoragePort
from app.domains.email.domain.entity.email import Email
from app.domains.email.domain.value_object.email_source import EmailSource
from app.domains.email.domain.value_object.parsed_status import ParsedStatus
from app.infrastructure.config.settings import get_settings
from app.infrastructure.external.timezone import to_app_tz

logger = logging.getLogger(__name__)


class GmailConnector(EmailConnectorPort):
    source_name: str = "gmail"

    def __init__(self, token_storage: OAuthTokenStoragePort):
        self._token_storage = token_storage
        self._creds_cache: dict[str, Credentials] = {}

    async def authenticate(self, *, account: str, user_id: int | None) -> None:
        creds = await self._load_credentials(account=account)
        # refresh가 필요하면 동기 호출이라 to_thread
        if creds.expired and creds.refresh_token:
            await asyncio.to_thread(creds.refresh, GoogleAuthRequest())
            await self._persist_refreshed_credentials(account=account, user_id=user_id, creds=creds)
        self._creds_cache[account] = creds

    async def fetch_emails(
        self,
        *,
        account: str,
        since: datetime | None,
        until: datetime | None,
        user_id: int | None,
    ) -> AsyncIterator[Email]:
        creds = self._creds_cache.get(account)
        if creds is None:
            await self.authenticate(account=account, user_id=user_id)
            creds = self._creds_cache[account]

        query = _build_gmail_query(since=since, until=until)
        page_token: str | None = None
        while True:
            page = await asyncio.to_thread(
                _list_messages_page, creds=creds, query=query, page_token=page_token
            )
            for msg_meta in page.get("messages", []):
                msg_full = await asyncio.to_thread(
                    _get_message_full, creds=creds, message_id=msg_meta["id"]
                )
                yield _to_email_entity(account=account, raw=msg_full)
            page_token = page.get("nextPageToken")
            if not page_token:
                break

    async def apply_label(
        self, *, account: str, message_id: str, label: str, user_id: int | None
    ) -> None:
        creds = self._creds_cache.get(account)
        if creds is None:
            await self.authenticate(account=account, user_id=user_id)
            creds = self._creds_cache[account]
        await asyncio.to_thread(_apply_label_sync, creds=creds, message_id=message_id, label=label)

    async def _load_credentials(self, *, account: str) -> Credentials:
        token = await self._token_storage.load(source=str(EmailSource.GMAIL), account=account)
        if token is None:
            raise AppException(
                status_code=401,
                message=f"Gmail 계정 '{account}' 에 대한 OAuth 토큰이 없습니다. /auth/gmail/start 로 인증하세요.",
            )
        settings = get_settings()
        return Credentials(
            token=token.access_token,
            refresh_token=token.refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.gmail_oauth_client_id,
            client_secret=settings.gmail_oauth_client_secret,
            scopes=token.scopes,
            expiry=(
                token.expires_at.astimezone(timezone.utc).replace(tzinfo=None)
                if token.expires_at
                else None
            ),
        )

    async def _persist_refreshed_credentials(
        self, *, account: str, user_id: int | None, creds: Credentials
    ) -> None:
        from app.domains.email.domain.value_object.oauth_token import OAuthToken

        token = OAuthToken(
            source=str(EmailSource.GMAIL),
            account=account,
            access_token=creds.token,
            refresh_token=creds.refresh_token,
            expires_at=creds.expiry.replace(tzinfo=timezone.utc) if creds.expiry else None,
            scopes=list(creds.scopes or []),
            user_id=user_id,
        )
        await self._token_storage.save(token)


# --- 모듈 함수 (동기, asyncio.to_thread 로 호출) ---


def _build_gmail_query(*, since: datetime | None, until: datetime | None) -> str:
    parts: list[str] = []
    if since is not None:
        parts.append(f"after:{int(since.timestamp())}")
    if until is not None:
        parts.append(f"before:{int(until.timestamp())}")
    return " ".join(parts)


def _gmail_service(creds: Credentials) -> Any:
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def _list_messages_page(
    *, creds: Credentials, query: str, page_token: str | None
) -> dict[str, Any]:
    service = _gmail_service(creds)
    result = (
        service.users()
        .messages()
        .list(userId="me", q=query or None, maxResults=100, pageToken=page_token)
        .execute()
    )
    return dict(result)


def _get_message_full(*, creds: Credentials, message_id: str) -> dict[str, Any]:
    service = _gmail_service(creds)
    result = service.users().messages().get(userId="me", id=message_id, format="full").execute()
    return dict(result)


def _apply_label_sync(*, creds: Credentials, message_id: str, label: str) -> None:
    service = _gmail_service(creds)
    label_id = _ensure_label_id(service, label)
    service.users().messages().modify(
        userId="me", id=message_id, body={"addLabelIds": [label_id]}
    ).execute()


def _ensure_label_id(service: Any, label_name: str) -> str:
    labels = service.users().labels().list(userId="me").execute().get("labels", [])
    for label in labels:
        if label.get("name") == label_name:
            return str(label["id"])
    created = (
        service.users()
        .labels()
        .create(
            userId="me",
            body={
                "name": label_name,
                "labelListVisibility": "labelShow",
                "messageListVisibility": "show",
            },
        )
        .execute()
    )
    return str(created["id"])


def _to_email_entity(*, account: str, raw: dict[str, Any]) -> Email:
    headers = {h["name"].lower(): h["value"] for h in raw.get("payload", {}).get("headers", [])}
    subject = headers.get("subject", "")
    sender_raw = headers.get("from", "")
    _, sender_email = parseaddr(sender_raw)
    sender = sender_email or sender_raw

    received_at = _resolve_received_at(headers=headers, internal_date_ms=raw.get("internalDate"))
    body_text, body_html = _extract_body_parts(raw.get("payload", {}))
    labels = list(raw.get("labelIds", []))

    return Email(
        source=EmailSource.GMAIL,
        account=account,
        message_id=str(raw["id"]),
        sender=sender,
        subject=subject,
        received_at=received_at,
        body_text=body_text,
        body_html=body_html,
        labels=labels,
        parsed_status=ParsedStatus.PENDING,
    )


def _resolve_received_at(
    *, headers: dict[str, str], internal_date_ms: str | int | None
) -> datetime:
    """헤더의 ``Date`` 우선, 없거나 파싱 실패 시 Gmail ``internalDate`` (UTC ms) 사용."""
    date_header = headers.get("date")
    if date_header:
        try:
            return to_app_tz(parsedate_to_datetime(date_header))
        except (TypeError, ValueError):
            logger.warning("Date 헤더 파싱 실패: %s", date_header)
    if internal_date_ms is not None:
        ts = int(internal_date_ms) / 1000.0
        return to_app_tz(datetime.fromtimestamp(ts, tz=timezone.utc))
    return to_app_tz(datetime.now(tz=timezone.utc))


def _extract_body_parts(payload: dict[str, Any]) -> tuple[str, str]:
    """multipart payload에서 text/plain과 text/html을 재귀적으로 수집."""
    text_parts: list[str] = []
    html_parts: list[str] = []

    def walk(part: dict[str, Any]) -> None:
        mime = part.get("mimeType", "")
        body = part.get("body", {})
        data = body.get("data")
        if data:
            decoded = base64.urlsafe_b64decode(data + "===").decode("utf-8", errors="replace")
            if mime == "text/plain":
                text_parts.append(decoded)
            elif mime == "text/html":
                html_parts.append(decoded)
        for sub in part.get("parts", []) or []:
            walk(sub)

    walk(payload)
    return "\n".join(text_parts), "\n".join(html_parts)
