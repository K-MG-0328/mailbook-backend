"""parser_routes.yaml 로더.

각 항목은 발신자 도메인/주소 또는 제목 키워드를 ``parser_name`` 으로 매핑한다.
실제 라우팅은 ``Parser.can_parse`` 가 담당하므로 이 파일은 운영 가시성/오버라이드용.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass(slots=True)
class ParserRoute:
    parser_name: str
    sender_patterns: list[str] = field(default_factory=list)
    subject_patterns: list[str] = field(default_factory=list)


def load_parser_routes(path: str | Path) -> list[ParserRoute]:
    p = Path(path)
    if not p.exists():
        return []
    with p.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    routes: list[ParserRoute] = []
    for item in raw.get("routes", []):
        routes.append(
            ParserRoute(
                parser_name=str(item["parser"]),
                sender_patterns=[str(p) for p in item.get("sender_patterns", [])],
                subject_patterns=[str(p) for p in item.get("subject_patterns", [])],
            )
        )
    return routes
