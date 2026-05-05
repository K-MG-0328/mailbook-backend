"""card_companies.yaml 로더 (PRD 8.3 스펙)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass(slots=True)
class CardCompanyEntry:
    name: str
    parser: str
    sender_domains: list[str] = field(default_factory=list)
    subject_keywords: list[str] = field(default_factory=list)


def load_card_companies(path: str | Path) -> list[CardCompanyEntry]:
    p = Path(path)
    if not p.exists():
        return []
    with p.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    entries: list[CardCompanyEntry] = []
    for item in raw.get("card_companies", []):
        entries.append(
            CardCompanyEntry(
                name=str(item["name"]).strip(),
                parser=str(item["parser"]).strip(),
                sender_domains=[str(d) for d in item.get("sender_domains", [])],
                subject_keywords=[str(k) for k in item.get("subject_keywords", [])],
            )
        )
    return entries
