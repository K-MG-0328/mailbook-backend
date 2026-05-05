from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from email import message_from_bytes
from email.policy import default as default_policy
from email.utils import parseaddr, parsedate_to_datetime
from pathlib import Path

from app.domains.payment_event.adapter.outbound.parsers.merchant.trancy_parser import (
    TrancyParser,
)
from app.domains.payment_event.domain.value_object.event_type import EventType
from app.infrastructure.external.timezone import to_app_tz

FIXTURES_DIR = Path(__file__).resolve().parents[3] / "fixtures" / "emails" / "gmail" / "trancy"


@dataclass
class FakeEmail:
    sender: str
    subject: str
    body_text: str
    body_html: str
    received_at: datetime


def _load_eml(name: str) -> FakeEmail:
    raw = (FIXTURES_DIR / name).read_bytes()
    msg = message_from_bytes(raw, policy=default_policy)
    sender_raw = str(msg.get("From", ""))
    _, sender_email = parseaddr(sender_raw)
    sender = sender_email or sender_raw
    subject = str(msg.get("Subject", ""))
    date_header = str(msg.get("Date", ""))
    received_at = (
        to_app_tz(parsedate_to_datetime(date_header)) if date_header else to_app_tz(datetime.now())
    )

    body_text = ""
    body_html = ""
    ctype = msg.get_content_type()
    payload = msg.get_payload(decode=True)
    decoded = (
        payload.decode("utf-8", errors="replace")
        if isinstance(payload, bytes)
        else str(payload or "")
    )
    if ctype == "text/plain":
        body_text = decoded
    elif ctype == "text/html":
        body_html = decoded

    return FakeEmail(
        sender=sender,
        subject=subject,
        body_text=body_text,
        body_html=body_html,
        received_at=received_at,
    )


def test_can_parse_matches_trancy_email() -> None:
    parser = TrancyParser()
    email = _load_eml("success_basic.eml")
    assert parser.can_parse(email) is True


def test_parse_extracts_expected_fields() -> None:
    parser = TrancyParser()
    email = _load_eml("success_basic.eml")
    expected = json.loads((FIXTURES_DIR / "success_basic.expected.json").read_text())

    result = parser.parse(email)

    assert result.success is True
    assert result.parser_name == expected["parser_name"]
    assert result.event_type == EventType.MERCHANT_RECEIPT
    assert result.merchant_name == expected["merchant_name"]
    assert result.amount == expected["amount"]
    assert result.card_company is None
    assert result.card_last4 is None
    assert result.confidence == expected["confidence"]
    assert result.paid_at is not None
    assert result.paid_at.isoformat() == expected["paid_at"]
    assert result.raw_data["invoice_number"] == expected["raw_data"]["invoice_number"]
    assert result.raw_data["receipt_number"] == expected["raw_data"]["receipt_number"]
    assert result.raw_data["payment_method"] == expected["raw_data"]["payment_method"]


def test_parse_fails_when_amount_missing() -> None:
    parser = TrancyParser()
    email = _load_eml("missing_amount.eml")

    result = parser.parse(email)

    assert result.success is False
    assert result.failure_reason is not None
    assert "amount" in result.failure_reason


def test_can_parse_false_for_other_sender() -> None:
    parser = TrancyParser()
    email = _load_eml("wrong_sender.eml")
    assert parser.can_parse(email) is False


def test_can_parse_false_for_other_subject() -> None:
    parser = TrancyParser()
    email = _load_eml("wrong_subject.eml")
    assert parser.can_parse(email) is False
