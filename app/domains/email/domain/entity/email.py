"""``Email`` Entity (PRD 2.1 emails 테이블)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.domains.email.domain.value_object.email_source import EmailSource
from app.domains.email.domain.value_object.parsed_status import ParsedStatus


@dataclass(slots=True)
class Email:
    source: EmailSource
    account: str
    message_id: str
    sender: str
    subject: str
    received_at: datetime
    body_text: str = ""
    body_html: str = ""
    labels: list[str] = field(default_factory=list)
    parsed_status: ParsedStatus = ParsedStatus.PENDING
    parse_failure_reason: str | None = None
    user_id: int | None = None
    id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
