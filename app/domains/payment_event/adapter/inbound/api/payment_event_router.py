from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response.base_response import BaseResponse
from app.domains.email.adapter.outbound.orchestration.email_query_adapter import EmailQueryAdapter
from app.domains.email.adapter.outbound.orchestration.email_status_updater_adapter import (
    EmailStatusUpdaterAdapter,
)
from app.domains.email.adapter.outbound.persistence.email_repository import EmailRepository
from app.domains.payment_event.adapter.outbound.external.anthropic_llm_parser import (
    AnthropicLlmParser,
)
from app.domains.payment_event.adapter.outbound.parsers.provider import StaticParserProvider
from app.domains.payment_event.adapter.outbound.persistence.payment_event_repository import (
    PaymentEventRepository,
)
from app.domains.payment_event.application.response.payment_event_response import (
    ParseSummaryResponse,
    PaymentEventResponse,
)
from app.domains.payment_event.application.usecase.parse_pending_emails import ParsePendingEmails
from app.infrastructure.config.settings import get_settings
from app.infrastructure.database.database import get_db

router = APIRouter(prefix="/payment-events", tags=["payment-events"])

SessionDep = Annotated[AsyncSession, Depends(get_db)]


@router.get("", response_model=BaseResponse[list[PaymentEventResponse]])
async def list_payment_events(
    session: SessionDep,
    matched: Annotated[
        bool | None, Query(description="None=전체, True=매칭됨, False=미매칭")
    ] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> BaseResponse[list[PaymentEventResponse]]:
    settings = get_settings()
    repo = PaymentEventRepository(session)
    events = await repo.list_recent(
        user_id=settings.owner_user_id, matched=matched, limit=limit, offset=offset
    )
    return BaseResponse.ok(data=[PaymentEventResponse.from_entity(e) for e in events])


@router.post("/parse", response_model=BaseResponse[ParseSummaryResponse])
async def parse_pending_endpoint(
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=1000)] = 200,
) -> BaseResponse[ParseSummaryResponse]:
    settings = get_settings()
    email_repo = EmailRepository(session)
    usecase = ParsePendingEmails(
        email_query=EmailQueryAdapter(email_repo),
        email_updater=EmailStatusUpdaterAdapter(email_repo),
        parser_provider=StaticParserProvider(),
        payment_event_repo=PaymentEventRepository(session),
        llm_parser=AnthropicLlmParser(),
    )
    summary = await usecase.execute(user_id=settings.owner_user_id, limit=limit)
    await session.commit()
    return BaseResponse.ok(
        data=ParseSummaryResponse(
            parsed=summary.parsed,
            skipped=summary.skipped,
            failed=summary.failed,
            llm_invoked=summary.llm_invoked,
        )
    )
