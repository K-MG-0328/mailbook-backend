"""``ParsePendingEmails`` usecase의 입력. email 도메인에서 변환되어 전달됨.

EmailLike Protocol을 구조적으로 만족하므로 Parser에 그대로 전달 가능.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class PendingEmail:
    id: int
    sender: str
    subject: str
    body_text: str
    body_html: str
    received_at: datetime
