from __future__ import annotations

from app.domains.email.domain.entity.email import Email
from app.domains.email.domain.value_object.email_source import EmailSource
from app.domains.email.domain.value_object.parsed_status import ParsedStatus
from app.domains.email.infrastructure.orm.email_orm import EmailORM


def _labels_to_str(labels: list[str]) -> str:
    return ",".join(labels)


def _str_to_labels(s: str) -> list[str]:
    return [x for x in s.split(",") if x]


def to_entity(orm: EmailORM) -> Email:
    return Email(
        id=orm.id,
        user_id=orm.user_id,
        source=EmailSource(orm.source),
        account=orm.account,
        message_id=orm.message_id,
        sender=orm.sender,
        subject=orm.subject,
        received_at=orm.received_at,
        body_text=orm.body_text,
        body_html=orm.body_html,
        labels=_str_to_labels(orm.labels),
        parsed_status=ParsedStatus(orm.parsed_status),
        parse_failure_reason=orm.parse_failure_reason,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


def to_orm(entity: Email) -> EmailORM:
    return EmailORM(
        user_id=entity.user_id,
        source=str(entity.source),
        account=entity.account,
        message_id=entity.message_id,
        sender=entity.sender,
        subject=entity.subject,
        received_at=entity.received_at,
        body_text=entity.body_text,
        body_html=entity.body_html,
        labels=_labels_to_str(entity.labels),
        parsed_status=str(entity.parsed_status),
        parse_failure_reason=entity.parse_failure_reason,
    )
