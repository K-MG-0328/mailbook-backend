from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class FetchEmailsRequest(BaseModel):
    account: str = Field(..., min_length=1)
    since: datetime | None = None
    until: datetime | None = None
