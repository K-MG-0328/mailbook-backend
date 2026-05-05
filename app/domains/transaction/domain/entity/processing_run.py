from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

ErrorRecord = dict[str, object]


@dataclass(slots=True)
class ProcessingRun:
    started_at: datetime
    finished_at: datetime | None = None
    emails_fetched: int = 0
    events_parsed: int = 0
    transactions_created: int = 0
    errors: list[ErrorRecord] = field(default_factory=list)
    user_id: int | None = None
    id: int | None = None
    created_at: datetime | None = None
