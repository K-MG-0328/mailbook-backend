"""정적 파서 인스턴스 풀. PR 5 에서 카드사/가맹점 파서가 추가되면 여기 등록."""

from __future__ import annotations

from app.domains.payment_event.application.port.parser_provider_port import ParserProviderPort
from app.domains.payment_event.domain.service.parser import Parser


class StaticParserProvider(ParserProviderPort):
    """``__init__`` 에 직접 인스턴스를 주입하거나, 모듈 레벨 ``DEFAULT_PARSERS`` 사용."""

    def __init__(self, parsers: list[Parser] | None = None):
        self._parsers = parsers if parsers is not None else list(DEFAULT_PARSERS)

    def list_parsers(self) -> list[Parser]:
        return list(self._parsers)


# PR 5 에서 카드사/가맹점 파서 import 후 이 리스트에 추가.
# 등록 순서가 곧 매칭 우선순위 (parser_registry.select_parser).
DEFAULT_PARSERS: list[Parser] = []
