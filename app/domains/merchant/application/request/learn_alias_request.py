from __future__ import annotations

from pydantic import BaseModel, Field


class LearnAliasRequest(BaseModel):
    raw_name: str = Field(..., min_length=1, max_length=255)
    canonical: str = Field(..., min_length=1, max_length=255)
    category: str | None = Field(default=None, max_length=50)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
