"""Orchestrator: fetch → parse → match → resolve_solo → ProcessingRun 기록.

각 단계는 같은 ``AsyncSession`` 안에서 실행되지만 단계 끝마다 commit 해 transaction 을
분리한다 (긴 트랜잭션으로 인한 idle 타임아웃 회피). Redis 락 (sync_lock) 은 라우터 책임.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.transaction.application.port.email_fetch_port import EmailFetchPort
from app.domains.transaction.application.port.event_parse_port import EventParsePort
from app.domains.transaction.application.usecase.match_unmatched_events import (
    MatchUnmatchedEvents,
)
from app.domains.transaction.application.usecase.resolve_solo_transactions import (
    ResolveSoloTransactions,
)
from app.domains.transaction.domain.entity.processing_run import ProcessingRun
from app.infrastructure.external.timezone import now_in_app_tz

ProcessingRunSaver = Callable[[ProcessingRun], Awaitable[ProcessingRun]]

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class SyncPipelineResult:
    run: ProcessingRun
    emails_fetched: int = 0
    events_parsed: int = 0
    events_skipped: int = 0
    events_failed: int = 0
    llm_invoked: int = 0
    transactions_created: int = 0
    review_required: int = 0
    solo_subscription: int = 0
    solo_non_card: int = 0
    errors: list[dict[str, object]] = field(default_factory=list)


@dataclass(slots=True)
class SyncPipeline:
    session: AsyncSession
    email_fetch: EmailFetchPort
    event_parse: EventParsePort
    match: MatchUnmatchedEvents
    resolve_solo: ResolveSoloTransactions
    processing_run_create: ProcessingRunSaver
    processing_run_update: ProcessingRunSaver

    async def execute(
        self,
        *,
        account: str,
        since: datetime | None,
        until: datetime | None,
        user_id: int | None,
    ) -> SyncPipelineResult:
        run = await self.processing_run_create(
            ProcessingRun(started_at=now_in_app_tz(), user_id=user_id)
        )
        await self.session.commit()

        result = SyncPipelineResult(run=run)

        # Step 1: fetch
        try:
            result.emails_fetched = await self.email_fetch.fetch(
                account=account, since=since, until=until, user_id=user_id
            )
            await self.session.commit()
        except Exception as exc:
            logger.exception("sync.fetch 실패")
            result.errors.append({"step": "fetch", "error": str(exc)})
            await self.session.rollback()

        # Step 2: parse
        try:
            parse_summary = await self.event_parse.parse_pending(user_id=user_id, limit=500)
            result.events_parsed = parse_summary.parsed
            result.events_skipped = parse_summary.skipped
            result.events_failed = parse_summary.failed
            result.llm_invoked = parse_summary.llm_invoked
            await self.session.commit()
        except Exception as exc:
            logger.exception("sync.parse 실패")
            result.errors.append({"step": "parse", "error": str(exc)})
            await self.session.rollback()

        # Step 3: match
        try:
            match_summary = await self.match.execute(user_id=user_id, limit=500)
            result.transactions_created += match_summary.matched
            result.review_required = match_summary.review_required
            await self.session.commit()
        except Exception as exc:
            logger.exception("sync.match 실패")
            result.errors.append({"step": "match", "error": str(exc)})
            await self.session.rollback()

        # Step 4: solo (24h timeout)
        try:
            solo_summary = await self.resolve_solo.execute(user_id=user_id, limit=500)
            result.solo_subscription = solo_summary.subscription
            result.solo_non_card = solo_summary.non_card
            result.transactions_created += solo_summary.subscription + solo_summary.non_card
            await self.session.commit()
        except Exception as exc:
            logger.exception("sync.resolve_solo 실패")
            result.errors.append({"step": "resolve_solo", "error": str(exc)})
            await self.session.rollback()

        # Step 5: ProcessingRun 갱신
        run.finished_at = now_in_app_tz()
        run.emails_fetched = result.emails_fetched
        run.events_parsed = result.events_parsed
        run.transactions_created = result.transactions_created
        run.errors = result.errors
        await self.processing_run_update(run)
        await self.session.commit()
        return result
