from app.domains.merchant.domain.service.alias_resolver import normalize_raw_name


def test_normalize_strips_whitespace_and_casefolds() -> None:
    assert normalize_raw_name("  Coupang  ") == "coupang"


def test_normalize_collapses_internal_whitespace() -> None:
    assert normalize_raw_name("STAR\tBUCKS  KOREA") == "star bucks korea"


def test_normalize_drops_korean_corp_suffix() -> None:
    assert normalize_raw_name("쿠팡(주)") == "쿠팡"
    assert normalize_raw_name("우아한형제들주식회사") == "우아한형제들"


def test_normalize_strips_pg_prefix() -> None:
    assert normalize_raw_name("KCP_쿠팡") == "쿠팡"
    assert normalize_raw_name("toss_스타벅스") == "스타벅스"


def test_normalize_empty_returns_empty() -> None:
    assert normalize_raw_name("") == ""
    assert normalize_raw_name("   ") == ""
