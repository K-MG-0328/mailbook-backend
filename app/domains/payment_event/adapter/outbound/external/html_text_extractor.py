"""HTML 본문에서 텍스트만 추출. selectolax 가 lxml 보다 빠르고 의존성 적음."""

from __future__ import annotations

from selectolax.parser import HTMLParser


def html_to_text(html: str) -> str:
    if not html:
        return ""
    tree = HTMLParser(html)
    # 스크립트/스타일 제거
    for tag in tree.css("script, style"):
        tag.decompose()
    text = tree.text(separator=" ", strip=True)
    return " ".join(text.split())
