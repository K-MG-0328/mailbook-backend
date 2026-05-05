"""파서 라우팅 알고리즘 (순수 함수). 등록된 파서 목록에서 매칭되는 첫 파서를 선택."""

from __future__ import annotations

from app.domains.payment_event.domain.service.parser import EmailLike, Parser


def select_parser(parsers: list[Parser], email: EmailLike) -> Parser | None:
    """등록 순서대로 ``can_parse`` 가 True 인 첫 파서를 반환."""
    for parser in parsers:
        if parser.can_parse(email):
            return parser
    return None
