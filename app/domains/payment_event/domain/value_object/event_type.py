from __future__ import annotations

from enum import StrEnum


class EventType(StrEnum):
    MERCHANT_RECEIPT = "merchant_receipt"
    CARD_NOTIFICATION = "card_notification"

    def opposite(self) -> "EventType":
        return (
            EventType.CARD_NOTIFICATION
            if self == EventType.MERCHANT_RECEIPT
            else EventType.MERCHANT_RECEIPT
        )
