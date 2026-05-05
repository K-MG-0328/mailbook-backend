"""LLM 으로 매칭 후보 중 1개 선택 (PRD 2.2 Step 3c)."""

from __future__ import annotations

import json
import logging

from anthropic import AsyncAnthropic

from app.domains.transaction.application.port.llm_disambiguator_port import LlmDisambiguatorPort
from app.domains.transaction.application.port.payment_event_query_port import CandidateEventDto
from app.infrastructure.config.settings import get_settings
from app.infrastructure.external.anthropic_client import sanitize_for_llm

logger = logging.getLogger(__name__)

_SYSTEM = (
    "당신은 결제 이벤트 매칭 판단자입니다. 가맹점 영수증과 카드사 결제 알림 두 종류의 "
    "이벤트가 같은 거래인지 판단합니다. 입력은 source 이벤트 1건과 candidates 여러 건 "
    "(같은 금액, ±10분, 반대 타입, card_last4 매칭 모호) 입니다. "
    "정확히 한 후보가 source 와 같은 거래라고 확신하면 그 id 를 반환하고, "
    "그렇지 않으면 null 을 반환하세요. 응답은 다음 JSON 만:\n"
    '{"chosen_id": <int|null>, "reason": <짧은 한국어 설명>}'
)


class AnthropicDisambiguator(LlmDisambiguatorPort):
    def __init__(self, client: AsyncAnthropic | None = None):
        self._settings = get_settings()
        self._client = client or AsyncAnthropic(api_key=self._settings.anthropic_api_key)

    async def pick(
        self, *, source: CandidateEventDto, candidates: list[CandidateEventDto]
    ) -> int | None:
        if not candidates:
            return None
        try:
            response = await self._client.messages.create(
                model=self._settings.llm_disambiguator_model,
                max_tokens=256,
                system=_SYSTEM,
                messages=[
                    {
                        "role": "user",
                        "content": _user_prompt(source, candidates),
                    }
                ],
            )
            text = "".join(
                getattr(block, "text", "") for block in response.content if block.type == "text"
            )
            payload = _parse_json(text)
            chosen = payload.get("chosen_id")
            if chosen is None:
                return None
            if not isinstance(chosen, (int, str)):
                return None
            try:
                return int(chosen)
            except (ValueError, TypeError):
                return None
        except Exception:
            logger.exception("LLM disambiguator 호출 실패")
            return None


def _user_prompt(source: CandidateEventDto, candidates: list[CandidateEventDto]) -> str:
    def _row(e: CandidateEventDto) -> dict[str, object]:
        return {
            "id": e.id,
            "event_type": e.event_type,
            "merchant_name": sanitize_for_llm(e.merchant_name),
            "amount": e.amount,
            "paid_at": e.paid_at.isoformat(),
            "card_company": e.card_company,
            "card_last4": e.card_last4,
        }

    payload = {
        "source": _row(source),
        "candidates": [_row(c) for c in candidates],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _parse_json(text: str) -> dict[str, object]:
    stripped = text.strip()
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end == -1:
        return {}
    parsed = json.loads(stripped[start : end + 1])
    return parsed if isinstance(parsed, dict) else {}
