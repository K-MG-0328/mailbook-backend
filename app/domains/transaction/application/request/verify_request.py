from __future__ import annotations

from pydantic import BaseModel, Field


class VerifyTransactionRequest(BaseModel):
    is_verified: bool = True
    note: str | None = Field(default=None, max_length=500)
