"""Trancy 영수증 파서.

가맹점이 직접 보내는 결제 영수증 메일을 파싱한다.
- 발신자: support@trancy.org
- 제목: "Receipt from Trancy (Invoice #...)"
- 본문: HTML 단독(text/html). body_text가 비어 html_to_text fallback 필요
- 결제수단: Naver Pay 등 PG. card_company/card_last4 부재
"""

from __future__ import annotations

import re

from app.domains.payment_event.adapter.outbound.external.html_text_extractor import html_to_text
from app.domains.payment_event.domain.service.parser import EmailLike, Parser
from app.domains.payment_event.domain.value_object.event_type import EventType
from app.domains.payment_event.domain.value_object.parse_result import ParseResult

PARSER_NAME = "trancy"
MERCHANT_CANONICAL = "Trancy"

_AMOUNT_PATTERN = re.compile(r"₩\s*([\d,]+)")
_INVOICE_PATTERN = re.compile(r"Invoice\s+Number[:\s]+([A-Za-z0-9-]+)", re.IGNORECASE)
_RECEIPT_PATTERN = re.compile(r"Receipt\s+Number[:\s]+([\d-]+)", re.IGNORECASE)
_PAYMENT_METHOD_PATTERN = re.compile(
    r"Payment\s+Method[:\s]+([A-Z][A-Za-z]*(?:\s+[A-Z][A-Za-z]*)?)"
)


class TrancyParser(Parser):
    name = PARSER_NAME
    sender_patterns = ["@trancy.org"]
    subject_patterns = ["Receipt from Trancy"]

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
            amount = int(amount_match.group(1).replace(",", ""))
        except ValueError:
            return ParseResult.fail(parser_name=PARSER_NAME, reason="amount 정수 변환 실패")

        # Trancy 본문은 일자만(시간 없음) → Gmail connector가 KST aware로 채운 헤더 Date 사용
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

        return ParseResult(
            success=True,
            parser_name=PARSER_NAME,
            event_type=EventType.MERCHANT_RECEIPT,
            merchant_name=MERCHANT_CANONICAL,
            amount=amount,
            paid_at=paid_at,
            card_company=None,
            card_last4=None,
            confidence=1.0,
            raw_data=raw_data,
        )
