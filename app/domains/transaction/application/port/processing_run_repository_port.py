from __future__ import annotations

from abc import ABC, abstractmethod

from app.domains.transaction.domain.entity.processing_run import ProcessingRun


class ProcessingRunRepositoryPort(ABC):
    @abstractmethod
    async def create(self, run: ProcessingRun) -> ProcessingRun: ...

    @abstractmethod
    async def update(self, run: ProcessingRun) -> ProcessingRun: ...

    @abstractmethod
    async def list_recent(self, *, user_id: int | None, limit: int) -> list[ProcessingRun]: ...
