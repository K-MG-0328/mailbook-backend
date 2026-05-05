from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.domains.email.domain.entity.email import Email


class EmailResponse(BaseModel):
    id: int
    source: str
    account: str
    message_id: str
    sender: str
    subject: str
    received_at: datetime
    parsed_status: str
    parse_failure_reason: str | None = None

    @classmethod
    def from_entity(cls, email: Email) -> "EmailResponse":
        if email.id is None:
            raise ValueError("저장되지 않은 Email 은 응답으로 변환할 수 없습니다.")
        return cls(
            id=email.id,
            source=str(email.source),
            account=email.account,
            message_id=email.message_id,
            sender=email.sender,
            subject=email.subject,
            received_at=email.received_at,
            parsed_status=str(email.parsed_status),
            parse_failure_reason=email.parse_failure_reason,
        )
