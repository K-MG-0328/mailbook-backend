from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response.base_response import BaseResponse
from app.domains.email.adapter.outbound.external.google_oauth_flow import GoogleOAuthFlow
from app.domains.email.adapter.outbound.persistence.email_repository import EmailRepository
from app.domains.email.adapter.outbound.persistence.encrypted_token_storage import (
    EncryptedTokenStorage,
)
from app.domains.email.application.response.email_response import EmailResponse
from app.domains.email.application.response.oauth_url_response import OAuthUrlResponse
from app.domains.email.application.usecase.complete_oauth import CompleteOAuth
from app.domains.email.application.usecase.start_oauth import StartOAuth
from app.domains.email.domain.value_object.parsed_status import ParsedStatus
from app.infrastructure.config.settings import get_settings
from app.infrastructure.database.database import get_db

router = APIRouter(tags=["email"])

SessionDep = Annotated[AsyncSession, Depends(get_db)]


def get_oauth_flow() -> GoogleOAuthFlow:
    return GoogleOAuthFlow()


OAuthFlowDep = Annotated[GoogleOAuthFlow, Depends(get_oauth_flow)]


@router.get("/auth/gmail/start", response_model=BaseResponse[OAuthUrlResponse])
async def gmail_oauth_start(flow: OAuthFlowDep) -> BaseResponse[OAuthUrlResponse]:
    request = await StartOAuth(flow=flow).execute()
    return BaseResponse.ok(
        data=OAuthUrlResponse(authorization_url=request.authorization_url, state=request.state)
    )


@router.get("/auth/gmail/callback")
async def gmail_oauth_callback(
    session: SessionDep,
    flow: OAuthFlowDep,
    code: Annotated[str, Query(...)],
    state: Annotated[str | None, Query()] = None,
    error: Annotated[str | None, Query()] = None,
) -> RedirectResponse:
    if error:
        raise HTTPException(status_code=400, detail=f"OAuth 거부: {error}")
    settings = get_settings()
    storage = EncryptedTokenStorage(session)
    token = await CompleteOAuth(flow=flow, storage=storage).execute(
        code=code, state=state, user_id=settings.owner_user_id
    )
    await session.commit()
    # 프론트엔드로 리다이렉트 (성공 표시 쿼리 포함)
    return RedirectResponse(
        url=f"{settings.cors_allowed_frontend_url}/?auth=success&account={token.account}",
        status_code=302,
    )


@router.get("/emails", response_model=BaseResponse[list[EmailResponse]])
async def list_emails(
    session: SessionDep,
    status: Annotated[ParsedStatus, Query(description="parsed_status 필터")] = ParsedStatus.PENDING,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> BaseResponse[list[EmailResponse]]:
    settings = get_settings()
    repo = EmailRepository(session)
    emails = await repo.list_by_status(
        user_id=settings.owner_user_id, status=status, limit=limit, offset=offset
    )
    return BaseResponse.ok(data=[EmailResponse.from_entity(e) for e in emails])
