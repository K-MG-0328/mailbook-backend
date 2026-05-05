import base64
from datetime import datetime, timezone

from app.domains.email.adapter.outbound.external.gmail_connector import (
    _build_gmail_query,
    _extract_body_parts,
    _resolve_received_at,
    _to_email_entity,
)
from app.domains.email.domain.value_object.email_source import EmailSource
from app.domains.email.domain.value_object.parsed_status import ParsedStatus


def _b64(s: str) -> str:
    return base64.urlsafe_b64encode(s.encode("utf-8")).decode("ascii")


def test_build_gmail_query_with_only_since() -> None:
    q = _build_gmail_query(since=datetime(2026, 4, 1, tzinfo=timezone.utc), until=None)
    assert q.startswith("after:")
    assert "before:" not in q


def test_build_gmail_query_empty_when_no_dates() -> None:
    assert _build_gmail_query(since=None, until=None) == ""


def test_resolve_received_at_prefers_date_header() -> None:
    headers = {"date": "Mon, 04 May 2026 10:30:00 +0900"}
    received = _resolve_received_at(headers=headers, internal_date_ms="0")
    # KST 변환 결과 — 시간대만 확인
    assert received.tzinfo is not None
    assert received.year == 2026
    assert received.month == 5
    assert received.day == 4


def test_resolve_received_at_falls_back_to_internal_date() -> None:
    received = _resolve_received_at(headers={}, internal_date_ms="1714780800000")
    assert received.tzinfo is not None


def test_extract_body_parts_handles_multipart() -> None:
    payload = {
        "mimeType": "multipart/alternative",
        "parts": [
            {"mimeType": "text/plain", "body": {"data": _b64("plain body")}},
            {"mimeType": "text/html", "body": {"data": _b64("<p>html body</p>")}},
        ],
    }
    text, html = _extract_body_parts(payload)
    assert text == "plain body"
    assert html == "<p>html body</p>"


def test_extract_body_parts_handles_nested_multipart() -> None:
    payload = {
        "mimeType": "multipart/mixed",
        "parts": [
            {
                "mimeType": "multipart/alternative",
                "parts": [
                    {"mimeType": "text/plain", "body": {"data": _b64("inner plain")}},
                ],
            },
        ],
    }
    text, html = _extract_body_parts(payload)
    assert text == "inner plain"
    assert html == ""


def test_to_email_entity_extracts_basic_fields() -> None:
    raw = {
        "id": "abc123",
        "labelIds": ["INBOX", "CATEGORY_PROMOTIONS"],
        "internalDate": "1714780800000",
        "payload": {
            "headers": [
                {"name": "From", "value": "결제 알림 <noreply@shinhancard.com>"},
                {"name": "Subject", "value": "[신한카드] 결제 안내"},
                {"name": "Date", "value": "Mon, 04 May 2026 10:30:00 +0900"},
            ],
            "mimeType": "text/plain",
            "body": {"data": _b64("결제 32500원")},
            "parts": [],
        },
    }
    email = _to_email_entity(account="me@example.com", raw=raw)
    assert email.source == EmailSource.GMAIL
    assert email.message_id == "abc123"
    assert email.sender == "noreply@shinhancard.com"
    assert email.subject == "[신한카드] 결제 안내"
    assert "결제 32500원" in email.body_text
    assert email.parsed_status == ParsedStatus.PENDING
    assert "INBOX" in email.labels
