"""email 도메인이 payment_event 의 ``EmailQueryPort`` 를 구현하는 wrapper."""

from __future__ import annotations

from app.domains.email.adapter.outbound.persistence.email_repository import EmailRepository
from app.domains.payment_event.application.port.email_query_port import EmailQueryPort
from app.domains.payment_event.application.request.pending_email import PendingEmail


class EmailQueryAdapter(EmailQueryPort):
    def __init__(self, repo: EmailRepository):
        self._repo = repo

    async def list_pending(self, *, user_id: int | None, limit: int) -> list[PendingEmail]:
        emails = await self._repo.list_pending(user_id=user_id, limit=limit)
        return [
            PendingEmail(
                id=e.id,
                sender=e.sender,
                subject=e.subject,
                body_text=e.body_text,
                body_html=e.body_html,
                received_at=e.received_at,
            )
            for e in emails
            if e.id is not None
        ]

    async def get_by_id(self, *, email_id: int) -> PendingEmail | None:
        # list_by_status 는 부적합 — 대신 직접 조회 메서드가 필요하다면 repository 확장.
        # 현재 ParsePendingEmails 는 list_pending 만 사용하므로 미구현으로 둔다.
        raise NotImplementedError("get_by_id 는 현재 사용처가 없습니다.")
