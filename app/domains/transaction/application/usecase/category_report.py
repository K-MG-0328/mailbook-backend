"""카테고리별 상세 리포트 — 카테고리 합계 + 가맹점별 분해."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from app.domains.transaction.application.port.transaction_repository_port import (
    TransactionRepositoryPort,
)
from app.domains.transaction.application.usecase.monthly_report import _month_range


@dataclass(slots=True)
class MerchantBreakdown:
    canonical_merchant: str
    total_amount: int
    count: int


@dataclass(slots=True)
class CategoryDetail:
    category: str
    total_amount: int
    count: int
    merchants: list[MerchantBreakdown] = field(default_factory=list)


@dataclass(slots=True)
class CategoryReportResult:
    year_month: str
    categories: list[CategoryDetail]


@dataclass(slots=True)
class CategoryReport:
    repo: TransactionRepositoryPort

    async def execute(self, *, user_id: int | None, year_month: str) -> CategoryReportResult:
        start, end = _month_range(year_month)
        txns = await self.repo.list_in_period(user_id=user_id, start=start, end=end)

        # category → merchant → (amount, count)
        buckets: dict[str, dict[str, list[int]]] = defaultdict(lambda: defaultdict(lambda: [0, 0]))
        for t in txns:
            cat = t.category or "기타"
            merchant = t.canonical_merchant or t.merchant_name or "(미상)"
            buckets[cat][merchant][0] += t.amount
            buckets[cat][merchant][1] += 1

        categories: list[CategoryDetail] = []
        for cat, merchants in sorted(
            buckets.items(),
            key=lambda kv: -sum(v[0] for v in kv[1].values()),
        ):
            merchant_list = [
                MerchantBreakdown(canonical_merchant=m, total_amount=v[0], count=v[1])
                for m, v in sorted(merchants.items(), key=lambda kv: -kv[1][0])
            ]
            total = sum(m.total_amount for m in merchant_list)
            count = sum(m.count for m in merchant_list)
            categories.append(
                CategoryDetail(
                    category=cat, total_amount=total, count=count, merchants=merchant_list
                )
            )
        return CategoryReportResult(year_month=year_month, categories=categories)
