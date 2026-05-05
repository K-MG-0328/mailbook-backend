from __future__ import annotations

from pydantic import BaseModel


class CategoryListResponse(BaseModel):
    categories: list[str]
