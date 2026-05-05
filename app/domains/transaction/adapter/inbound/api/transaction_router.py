from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response.base_response import BaseResponse
from app.domains.merchant.infrastructure.yaml_loader.categories_yaml_loader import (
    YamlCategoryCatalog,
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
from app.domains.transaction.adapter.outbound.persistence.transaction_repository import (
    TransactionRepository,
)
from app.domains.transaction.application.request.verify_request import VerifyTransactionRequest
from app.domains.transaction.application.response.transaction_response import (
    MatchSummaryResponse,
    SoloSummaryResponse,
    TransactionResponse,
)
from app.domains.transaction.application.usecase.list_transactions import (
    ListReviewRequired,
    ListTransactions,
)
from app.domains.transaction.application.usecase.match_unmatched_events import (
    MatchUnmatchedEvents,
)
from app.domains.transaction.application.usecase.resolve_solo_transactions import (
    ResolveSoloTransactions,
)
from app.domains.transaction.application.usecase.verify_transaction import VerifyTransaction
from app.domains.transaction.domain.service.classifier import Classifier
from app.infrastructure.config.settings import get_settings
from app.infrastructure.database.database import get_db

router = APIRouter(prefix="/transactions", tags=["transactions"])

SessionDep = Annotated[AsyncSession, Depends(get_db)]

_CONFIG_DIR = Path(__file__).resolve().parents[5] / "config"


def _build_classifier() -> Classifier:
    return Classifier(validator=YamlCategoryCatalog(_CONFIG_DIR / "categories.yaml"))


@router.get("", response_model=BaseResponse[list[TransactionResponse]])
async def list_transactions_endpoint(
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> BaseResponse[list[TransactionResponse]]:
    settings = get_settings()
    txns = await ListTransactions(TransactionRepository(session)).execute(
        user_id=settings.owner_user_id, limit=limit, offset=offset
    )
    return BaseResponse.ok(data=[TransactionResponse.from_entity(t) for t in txns])


@router.get("/review", response_model=BaseResponse[list[TransactionResponse]])
async def list_review_endpoint(
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> BaseResponse[list[TransactionResponse]]:
    settings = get_settings()
    txns = await ListReviewRequired(TransactionRepository(session)).execute(
        user_id=settings.owner_user_id, limit=limit, offset=offset
    )
    return BaseResponse.ok(data=[TransactionResponse.from_entity(t) for t in txns])


@router.post("/{transaction_id}/verify", response_model=BaseResponse[TransactionResponse])
async def verify_endpoint(
    transaction_id: int,
    payload: VerifyTransactionRequest,
    session: SessionDep,
) -> BaseResponse[TransactionResponse]:
    txn = await VerifyTransaction(TransactionRepository(session)).execute(
        transaction_id=transaction_id, is_verified=payload.is_verified, note=payload.note
    )
    await session.commit()
    return BaseResponse.ok(data=TransactionResponse.from_entity(txn))


@router.post("/match", response_model=BaseResponse[MatchSummaryResponse])
async def match_endpoint(
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=2000)] = 200,
) -> BaseResponse[MatchSummaryResponse]:
    settings = get_settings()
    usecase = MatchUnmatchedEvents(
        payment_events=PaymentEventQueryAdapter(session),
        transactions=TransactionRepository(session),
        fuzzy=RapidFuzzMatcher(),
        llm=AnthropicDisambiguator(),
        merchant_resolver=MerchantResolverAdapter(session),
        classifier=_build_classifier(),
    )
    summary = await usecase.execute(user_id=settings.owner_user_id, limit=limit)
    await session.commit()
    return BaseResponse.ok(
        data=MatchSummaryResponse(
            matched=summary.matched,
            review_required=summary.review_required,
            skipped=summary.skipped,
        )
    )


@router.post("/resolve-solo", response_model=BaseResponse[SoloSummaryResponse])
async def resolve_solo_endpoint(
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=2000)] = 200,
) -> BaseResponse[SoloSummaryResponse]:
    settings = get_settings()
    usecase = ResolveSoloTransactions(
        payment_events=PaymentEventQueryAdapter(session),
        transactions=TransactionRepository(session),
        merchant_resolver=MerchantResolverAdapter(session),
        classifier=_build_classifier(),
    )
    summary = await usecase.execute(user_id=settings.owner_user_id, limit=limit)
    await session.commit()
    return BaseResponse.ok(
        data=SoloSummaryResponse(subscription=summary.subscription, non_card=summary.non_card)
    )
