"""Anthropic Claude 기반 LLM 폴백 파서.

규칙 기반 파서가 처리 못한 메일에서 ParseResult를 추출. PRD 4.1: LLM 호출은
전체 메일의 10% 이하 유지가 목표 — 호출자(usecase)가 매칭 우선 원칙으로 빈도 제어.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime
from typing import Any

from anthropic import AsyncAnthropic

from app.domains.payment_event.application.port.llm_parser_port import LlmParserPort
from app.domains.payment_event.domain.service.parser import EmailLike
from app.domains.payment_event.domain.value_object.event_type import EventType
from app.domains.payment_event.domain.value_object.parse_result import ParseResult
from app.infrastructure.cache.redis_client import redis_client as _redis_client
from app.infrastructure.config.settings import get_settings
from app.infrastructure.external.anthropic_client import sanitize_for_llm
from app.infrastructure.external.timezone import to_app_tz

logger = logging.getLogger(__name__)

PARSER_NAME = "anthropic_llm_fallback"

_SYSTEM_PROMPT = (
    "당신은 한국어 결제 이메일 파서입니다. 입력된 이메일에서 결제 정보를 추출해 "
    "JSON 으로만 응답하세요. 불필요한 설명/마크다운 없이 JSON 본문만 출력하세요.\n\n"
    "응답 스키마:\n"
    "{\n"
    '  "success": boolean,                # 결제 정보를 신뢰할 수 있게 추출했는지\n'
    '  "event_type": "merchant_receipt" | "card_notification",\n'
    '  "merchant_name": string,\n'
    '  "amount": integer,                  # 원 단위 정수, 콤마/원자 제거\n'
    '  "paid_at": string,                  # ISO8601 with KST offset (+09:00) 권장\n'
    '  "card_company": string | null,\n'
    '  "card_last4": string | null,        # 4자리 숫자\n'
    '  "confidence": number                # 0.0 ~ 1.0\n'
    "}\n\n"
    "결제 정보가 명확하지 않으면 success=false 로 답하세요. "
    "외화 결제는 amount 에 원화 청구액이 있으면 그것을, 없으면 0 을 넣고 success=false 로 표시하세요."
)


class AnthropicLlmParser(LlmParserPort):
    def __init__(self, client: AsyncAnthropic | None = None):
        self._settings = get_settings()
        self._client = client or AsyncAnthropic(api_key=self._settings.anthropic_api_key)

    async def parse(self, email: EmailLike) -> ParseResult:
        cache_key = self._cache_key(email)
        cached = await self._read_cache(cache_key)
        if cached is not None:
            return _to_parse_result(cached)

        for attempt in range(2):  # PRD 7: retry 1회
            try:
                response = await self._client.messages.create(
                    model=self._settings.llm_parser_model,
                    max_tokens=512,
                    system=_SYSTEM_PROMPT,
                    messages=[
                        {
                            "role": "user",
                            "content": _user_prompt(email),
                        }
                    ],
                )
                text = "".join(
                    getattr(block, "text", "") for block in response.content if block.type == "text"
                )
                payload = _extract_json(text)
                await self._write_cache(cache_key, payload)
                return _to_parse_result(payload)
            except json.JSONDecodeError as exc:
                logger.warning("LLM 응답 JSON 파싱 실패 (attempt=%d): %s", attempt, exc)
            except Exception as exc:
                logger.exception("LLM 호출 실패 (attempt=%d)", attempt)
                if attempt == 1:
                    return ParseResult.fail(parser_name=PARSER_NAME, reason=f"LLM 오류: {exc}")
        return ParseResult.fail(
            parser_name=PARSER_NAME, reason="LLM 응답 JSON 파싱 실패 (2회 시도)"
        )

    def _cache_key(self, email: EmailLike) -> str:
        h = hashlib.sha256()
        h.update(email.sender.encode("utf-8"))
        h.update(b"|")
        h.update(email.subject.encode("utf-8"))
        h.update(b"|")
        h.update(email.body_text.encode("utf-8")[:4096])
        return f"llm_parser:{h.hexdigest()}"

    async def _read_cache(self, key: str) -> dict[str, Any] | None:
        try:
            raw = await _redis_client.get(key)
            if raw is None:
                return None
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else None
        except Exception:
            return None

    async def _write_cache(self, key: str, payload: dict[str, Any]) -> None:
        try:
            await _redis_client.set(
                key, json.dumps(payload), ex=self._settings.llm_cache_ttl_seconds
            )
        except Exception:
            pass


def _user_prompt(email: EmailLike) -> str:
    body = email.body_text or ""
    if not body and email.body_html:
        from app.domains.payment_event.adapter.outbound.external.html_text_extractor import (
            html_to_text,
        )

        body = html_to_text(email.body_html)
    body = sanitize_for_llm(body)[:6000]
    sender = sanitize_for_llm(email.sender)
    subject = sanitize_for_llm(email.subject)
    return (
        f"From: {sender}\nSubject: {subject}\nReceived: {email.received_at.isoformat()}\n\n"
        f"본문:\n{body}"
    )


def _extract_json(text: str) -> dict[str, Any]:
    """모델이 코드 블록으로 감쌌을 가능성을 고려해 첫 ``{ ... }`` 만 잘라낸다."""
    stripped = text.strip()
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise json.JSONDecodeError("JSON 객체가 응답에 없음", stripped, 0)
    snippet = stripped[start : end + 1]
    parsed = json.loads(snippet)
    if not isinstance(parsed, dict):
        raise json.JSONDecodeError("JSON 객체가 아님", snippet, 0)
    return parsed


def _to_parse_result(payload: dict[str, Any]) -> ParseResult:
    if not payload.get("success"):
        return ParseResult.fail(
            parser_name=PARSER_NAME,
            reason=str(payload.get("failure_reason") or "LLM success=false"),
        )
    try:
        event_type = EventType(payload["event_type"])
    except (KeyError, ValueError):
        return ParseResult.fail(parser_name=PARSER_NAME, reason="event_type 누락/오류")

    paid_at_raw = payload.get("paid_at")
    paid_at: datetime | None = None
    if paid_at_raw:
        try:
            paid_at = to_app_tz(datetime.fromisoformat(str(paid_at_raw).replace("Z", "+00:00")))
        except ValueError:
            return ParseResult.fail(parser_name=PARSER_NAME, reason="paid_at ISO8601 파싱 실패")

    if paid_at is None:
        return ParseResult.fail(parser_name=PARSER_NAME, reason="paid_at 누락")

    return ParseResult(
        success=True,
        parser_name=PARSER_NAME,
        event_type=event_type,
        merchant_name=str(payload.get("merchant_name", "")).strip(),
        amount=int(payload.get("amount", 0) or 0),
        paid_at=paid_at,
        card_company=payload.get("card_company"),
        card_last4=(str(payload.get("card_last4")).strip() if payload.get("card_last4") else None),
        confidence=float(payload.get("confidence", 0.5)),
        raw_data={"llm_payload": payload},
    )
