from __future__ import annotations

from pydantic import BaseModel


class OAuthUrlResponse(BaseModel):
    authorization_url: str
    state: str
