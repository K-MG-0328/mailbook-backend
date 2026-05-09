"""Anthropic 영수증 파서 (Stripe 발송).

- 발신자: invoice+statements@mail.anthropic.com
- 제목: "Your receipt from Anthropic, PBC #<receipt-no>"
- 본문: text/plain + text/html. body_text 가 채워져 있어 fallback 불필요하지만
  Trancy 와 동일하게 html_to_text fallback 도 둔다.
- 통화: USD 단독. amount 는 cents 단위 정수로 저장하고 raw_data["currency"]="USD".
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from app.domains.payment_event.adapter.outbound.external.html_text_extractor import html_to_text
from app.domains.payment_event.domain.service.parser import EmailLike, Parser
from app.domains.payment_event.domain.value_object.event_type import EventType
from app.domains.payment_event.domain.value_object.parse_result import ParseResult

PARSER_NAME = "anthropic"
MERCHANT_CANONICAL = "Anthropic"
CURRENCY = "USD"  # Stripe-issued Anthropic 영수증은 USD 단독.

_AMOUNT_PATTERN = re.compile(r"Amount paid\s+\$([\d,]+\.\d{2})")
_INVOICE_PATTERN = re.compile(r"Invoice number\s+([A-Z0-9-]+)")
_RECEIPT_PATTERN = re.compile(r"Receipt number\s+([\d-]+)")
_PAYMENT_METHOD_PATTERN = re.compile(
    r"Payment method[ \t]+([A-Z][A-Za-z]*(?:[ \t]+[A-Z][A-Za-z]*)?)"
)
# Stripe 영수증의 카드 결제 표기는 "Payment method <brand-image>? - 1234" 형태.
# html_to_text 가 brand 이미지를 제거하고 남는 "- 1234" 패턴을 잡는다.
_CARD_LAST4_PATTERN = re.compile(r"Payment method[^\r\n]*?-\s*(\d{4})")


class AnthropicParser(Parser):
    name = PARSER_NAME
    sender_patterns = ["@mail.anthropic.com"]
    subject_patterns = ["Your receipt from Anthropic"]

    def can_parse(self, email: EmailLike) -> bool:
        sender = email.sender.lower()
        sender_ok = any(p.lower() in sender for p in self.sender_patterns)
        subject_ok = any(p in email.subject for p in self.subject_patterns)
        return sender_ok and subject_ok

    def parse(self, email: EmailLike) -> ParseResult:
        text = email.body_text or html_to_text(email.body_html)
        if not text:
            return ParseResult.fail(parser_name=PARSER_NAME, reason="본문 비어있음")

        amount_match = _AMOUNT_PATTERN.search(text)
        if not amount_match:
            return ParseResult.fail(parser_name=PARSER_NAME, reason="amount 추출 실패")
        try:
            amount_cents = int(Decimal(amount_match.group(1).replace(",", "")) * 100)
        except (InvalidOperation, ValueError):
            return ParseResult.fail(parser_name=PARSER_NAME, reason="amount 정수 변환 실패")

        # Anthropic 본문의 "Paid May 3, 2026" 은 일자만이라 시간이 없음 →
        # Gmail connector 가 KST aware 로 채운 헤더 Date 를 사용 (Trancy 와 동일).
        paid_at = email.received_at
        if paid_at is None:
            return ParseResult.fail(parser_name=PARSER_NAME, reason="paid_at(received_at) 누락")

        raw_data: dict[str, object] = {}
        if (m := _INVOICE_PATTERN.search(text)) is not None:
            raw_data["invoice_number"] = m.group(1)
        if (m := _RECEIPT_PATTERN.search(text)) is not None:
            raw_data["receipt_number"] = m.group(1)
        if (m := _PAYMENT_METHOD_PATTERN.search(text)) is not None:
            raw_data["payment_method"] = m.group(1).strip()

        card_last4: str | None = None
        if (m := _CARD_LAST4_PATTERN.search(text)) is not None:
            card_last4 = m.group(1)

        return ParseResult(
            success=True,
            parser_name=PARSER_NAME,
            event_type=EventType.MERCHANT_RECEIPT,
            merchant_name=MERCHANT_CANONICAL,
            amount=amount_cents,
            currency=CURRENCY,
            paid_at=paid_at,
            card_company=None,
            card_last4=card_last4,
            confidence=1.0,
            raw_data=raw_data,
        )
