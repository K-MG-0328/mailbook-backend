"""정적 파서 인스턴스 풀. 새 가맹점 파서 추가 시 ``DEFAULT_PARSERS`` 에 등록."""

from __future__ import annotations

from app.domains.payment_event.adapter.outbound.parsers.merchant.anthropic_parser import (
    AnthropicParser,
)
from app.domains.payment_event.adapter.outbound.parsers.merchant.trancy_parser import (
    TrancyParser,
)
from app.domains.payment_event.application.port.parser_provider_port import ParserProviderPort
from app.domains.payment_event.domain.service.parser import Parser


class StaticParserProvider(ParserProviderPort):
    """``__init__`` 에 직접 인스턴스를 주입하거나, 모듈 레벨 ``DEFAULT_PARSERS`` 사용."""

    def __init__(self, parsers: list[Parser] | None = None):
        self._parsers = parsers if parsers is not None else list(DEFAULT_PARSERS)

    def list_parsers(self) -> list[Parser]:
        return list(self._parsers)


# 등록 순서가 곧 매칭 우선순위 (parser_registry.select_parser).
DEFAULT_PARSERS: list[Parser] = [TrancyParser(), AnthropicParser()]
