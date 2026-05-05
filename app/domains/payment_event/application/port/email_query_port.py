"""payment_event 도메인이 email 도메인 데이터를 읽기 위한 anti-corruption 포트.

구현체(wrapper adapter)는 email 도메인 outbound 영역에 위치한다.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.domains.payment_event.application.request.pending_email import PendingEmail


class EmailQueryPort(ABC):
    @abstractmethod
    async def list_pending(self, *, user_id: int | None, limit: int) -> list[PendingEmail]: ...

    @abstractmethod
    async def get_by_id(self, *, email_id: int) -> PendingEmail | None: ...
