from __future__ import annotations

from enum import StrEnum


class PaymentMethod(StrEnum):
    CARD = "card"
    SUBSCRIPTION = "subscription"  # card_notification 단독: 정기결제 추정
    NON_CARD = "non_card"  # merchant_receipt 단독: 계좌이체 등 추정
    UNKNOWN = "unknown"
