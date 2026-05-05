from datetime import datetime

from app.domains.payment_event.domain.service.parser import EmailLike, Parser
from app.domains.payment_event.domain.service.parser_registry import select_parser
from app.domains.payment_event.domain.value_object.parse_result import ParseResult


class _StubParser(Parser):
    def __init__(self, name: str, accepts_sender: str):
        self.name = name
        self.sender_patterns = [accepts_sender]
        self.subject_patterns: list[str] = []
        self._accepts = accepts_sender

    def can_parse(self, email: EmailLike) -> bool:
        return self._accepts in email.sender

    def parse(self, email: EmailLike) -> ParseResult:
        return ParseResult.fail(parser_name=self.name, reason="stub")


def _email(sender: str) -> EmailLike:
    class _E:
        pass

    e = _E()
    e.sender = sender
    e.subject = ""
    e.body_text = ""
    e.body_html = ""
    e.received_at = datetime(2026, 1, 1)
    return e  # type: ignore[return-value]


def test_select_parser_returns_first_match() -> None:
    parsers = [_StubParser("a", "shinhancard.com"), _StubParser("b", "coupang.com")]
    parser = select_parser(parsers, _email("noreply@coupang.com"))
    assert parser is not None
    assert parser.name == "b"


def test_select_parser_returns_none_when_no_match() -> None:
    parsers = [_StubParser("a", "shinhancard.com")]
    parser = select_parser(parsers, _email("noreply@something-else.com"))
    assert parser is None


def test_select_parser_respects_order() -> None:
    # 두 파서가 모두 매칭될 때 등록 순서가 우선순위
    p1 = _StubParser("first", ".com")
    p2 = _StubParser("second", ".com")
    parser = select_parser([p1, p2], _email("a@b.com"))
    assert parser is not None
    assert parser.name == "first"
