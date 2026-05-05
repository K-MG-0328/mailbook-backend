from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response.base_response import BaseResponse
from app.domains.email.adapter.outbound.orchestration.email_fetch_adapter import GmailFetchAdapter
from app.domains.merchant.infrastructure.yaml_loader.categories_yaml_loader import (
    YamlCategoryCatalog,
)
from app.domains.payment_event.adapter.outbound.orchestration.event_parse_adapter import (
    EventParseAdapter,
)
from app.domains.transaction.adapter.outbound.external.anthropic_disambiguator import (
    AnthropicDisambiguator,
)
from app.domains.transaction.adapter.outbound.external.rapidfuzz_matcher import RapidFuzzMatcher
from app.domains.transaction.adapter.outbound.persistence.merchant_resolver_adapter import (
    MerchantResolverAdapter,
)
from app.domains.transaction.adapter.outbound.persistence.payment_event_query_adapter import (
    PaymentEventQueryAdapter,
)
from app.domains.transaction.adapter.outbound.persistence.processing_run_repository import (
    ProcessingRunRepository,
)
from app.domains.transaction.adapter.outbound.persistence.transaction_repository import (
    TransactionRepository,
)
from app.domains.transaction.application.usecase.match_unmatched_events import (
    MatchUnmatchedEvents,
)
from app.domains.transaction.application.usecase.resolve_solo_transactions import (
    ResolveSoloTransactions,
)
from app.domains.transaction.application.usecase.sync_pipeline import (
    SyncPipeline,
    SyncPipelineResult,
)
from app.domains.transaction.domain.service.classifier import Classifier
from app.infrastructure.cache.redis_client import redis_client
from app.infrastructure.config.settings import get_settings
from app.infrastructure.database.database import get_db

router = APIRouter(prefix="/sync", tags=["sync"])

SessionDep = Annotated[AsyncSession, Depends(get_db)]

_CONFIG_DIR = Path(__file__).resolve().parents[5] / "config"
_SYNC_LOCK_KEY = "mailbook:sync_lock"


class SyncRequest(BaseModel):
    account: str
    since: datetime | None = None
    until: datetime | None = None


class SyncResponse(BaseModel):
    run_id: int | None
    emails_fetched: int
    events_parsed: int
    events_skipped: int
    events_failed: int
    llm_invoked: int
    transactions_created: int
    review_required: int
    solo_subscription: int
    solo_non_card: int
    errors: list[dict[str, object]]


def _to_response(result: SyncPipelineResult) -> SyncResponse:
    return SyncResponse(
        run_id=result.run.id,
        emails_fetched=result.emails_fetched,
        events_parsed=result.events_parsed,
        events_skipped=result.events_skipped,
        events_failed=result.events_failed,
        llm_invoked=result.llm_invoked,
        transactions_created=result.transactions_created,
        review_required=result.review_required,
        solo_subscription=result.solo_subscription,
        solo_non_card=result.solo_non_card,
        errors=result.errors,
    )


def _build_classifier() -> Classifier:
    return Classifier(validator=YamlCategoryCatalog(_CONFIG_DIR / "categories.yaml"))


@router.post("", response_model=BaseResponse[SyncResponse])
async def run_sync(payload: SyncRequest, session: SessionDep) -> BaseResponse[SyncResponse]:
    settings = get_settings()
    locked = await redis_client.set(_SYNC_LOCK_KEY, "1", nx=True, ex=settings.sync_lock_ttl_seconds)
    if not locked:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="다른 sync 작업이 진행 중입니다. 잠시 후 재시도하세요.",
        )
    try:
        run_repo = ProcessingRunRepository(session)
        pipeline = SyncPipeline(
            session=session,
            email_fetch=GmailFetchAdapter(session),
            event_parse=EventParseAdapter(session),
            match=MatchUnmatchedEvents(
                payment_events=PaymentEventQueryAdapter(session),
                transactions=TransactionRepository(session),
                fuzzy=RapidFuzzMatcher(),
                llm=AnthropicDisambiguator(),
                merchant_resolver=MerchantResolverAdapter(session),
                classifier=_build_classifier(),
            ),
            resolve_solo=ResolveSoloTransactions(
                payment_events=PaymentEventQueryAdapter(session),
                transactions=TransactionRepository(session),
                merchant_resolver=MerchantResolverAdapter(session),
                classifier=_build_classifier(),
            ),
            processing_run_create=run_repo.create,
            processing_run_update=run_repo.update,
        )
        result = await pipeline.execute(
            account=payload.account,
            since=payload.since,
            until=payload.until,
            user_id=settings.owner_user_id,
        )
        return BaseResponse.ok(data=_to_response(result))
    finally:
        await redis_client.delete(_SYNC_LOCK_KEY)
