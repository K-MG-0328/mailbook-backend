from __future__ import annotations

from app.domains.transaction.domain.entity.processing_run import ProcessingRun
from app.domains.transaction.infrastructure.orm.transaction_orm import ProcessingRunORM


def to_entity(orm: ProcessingRunORM) -> ProcessingRun:
    return ProcessingRun(
        id=orm.id,
        user_id=orm.user_id,
        started_at=orm.started_at,
        finished_at=orm.finished_at,
        emails_fetched=orm.emails_fetched,
        events_parsed=orm.events_parsed,
        transactions_created=orm.transactions_created,
        errors=list(orm.errors) if orm.errors else [],
        created_at=orm.created_at,
    )


def to_orm(entity: ProcessingRun) -> ProcessingRunORM:
    return ProcessingRunORM(
        user_id=entity.user_id,
        started_at=entity.started_at,
        finished_at=entity.finished_at,
        emails_fetched=entity.emails_fetched,
        events_parsed=entity.events_parsed,
        transactions_created=entity.transactions_created,
        errors=entity.errors if entity.errors else None,
    )
