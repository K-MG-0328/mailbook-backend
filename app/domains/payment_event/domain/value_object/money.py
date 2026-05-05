"""원 단위 정수 금액 (PRD 2.4 ParseResult.amount).

기본 통화는 KRW. 외화 결제는 raw_data 에 별도 보관 (PRD 7).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Money:
    won: int

    def __post_init__(self) -> None:
        if not isinstance(self.won, int) or isinstance(self.won, bool):
            raise TypeError("Money.won 은 정수여야 합니다.")
