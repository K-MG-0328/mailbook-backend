"""merchants.yaml 로더 (PRD 8.2 스펙). Application의 ``MerchantSeedRow`` DTO를 반환."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from app.domains.merchant.application.request.merchant_seed_row import MerchantSeedRow


def load_merchants_yaml(path: str | Path) -> list[MerchantSeedRow]:
    p = Path(path)
    if not p.exists():
        return []
    with p.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    return _parse(raw)


def parse_merchants_dict(raw: dict[str, Any]) -> list[MerchantSeedRow]:
    return _parse(raw)


def _parse(raw: dict[str, Any]) -> list[MerchantSeedRow]:
    rows: list[MerchantSeedRow] = []
    for item in raw.get("merchants", []):
        canonical = str(item["canonical"]).strip()
        aliases = [str(a).strip() for a in item.get("aliases", []) if str(a).strip()]
        category = item.get("category")
        rows.append(
            MerchantSeedRow(
                canonical=canonical,
                aliases=aliases,
                category=str(category).strip() if category else None,
            )
        )
    return rows
