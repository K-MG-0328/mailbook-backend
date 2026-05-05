from pathlib import Path

from app.domains.merchant.infrastructure.yaml_loader.categories_yaml_loader import (
    YamlCategoryCatalog,
)
from app.domains.merchant.infrastructure.yaml_loader.merchants_yaml_loader import (
    load_merchants_yaml,
    parse_merchants_dict,
)


def test_categories_yaml_loads_default_seed() -> None:
    repo_root = Path(__file__).resolve().parents[4]
    catalog = YamlCategoryCatalog(repo_root / "config" / "categories.yaml")
    names = {c.name for c in catalog.list_categories()}
    assert {"식비", "쇼핑", "교통", "기타"} <= names
    assert catalog.is_valid("쇼핑")
    assert not catalog.is_valid("없는카테고리")


def test_merchants_yaml_loads_default_seed() -> None:
    repo_root = Path(__file__).resolve().parents[4]
    rows = load_merchants_yaml(repo_root / "config" / "merchants.yaml")
    canonicals = {r.canonical for r in rows}
    assert "쿠팡" in canonicals
    coupang = next(r for r in rows if r.canonical == "쿠팡")
    assert coupang.category == "쇼핑"
    assert "Coupang Pay" in coupang.aliases


def test_parse_merchants_dict_handles_missing_optional_fields() -> None:
    rows = parse_merchants_dict({"merchants": [{"canonical": "AcmeOnly"}]})
    assert len(rows) == 1
    assert rows[0].aliases == []
    assert rows[0].category is None
