"""월별 가계부 집계 (PRD 5 Phase 1 DoD)."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from app.domains.transaction.application.port.transaction_repository_port import (
    TransactionRepositoryPort,
)
from app.infrastructure.config.settings import get_settings


@dataclass(slots=True)
class CategoryAggregate:
    category: str
    total_amount: int
    count: int


@dataclass(slots=True)
class MonthlyReportResult:
    year_month: str
    total_amount: int
    transaction_count: int
    by_category: list[CategoryAggregate]
    by_payment_method: list[CategoryAggregate]
    review_required_count: int = 0


@dataclass(slots=True)
class MonthlyReport:
    repo: TransactionRepositoryPort

    async def execute(self, *, user_id: int | None, year_month: str) -> MonthlyReportResult:
        start, end = _month_range(year_month)
        txns = await self.repo.list_in_period(user_id=user_id, start=start, end=end)

        category_totals: dict[str, list[int]] = defaultdict(lambda: [0, 0])
        method_totals: dict[str, list[int]] = defaultdict(lambda: [0, 0])
        total = 0
        review = 0
        for t in txns:
            total += t.amount
            cat = t.category or "기타"
            category_totals[cat][0] += t.amount
            category_totals[cat][1] += 1
            method_totals[str(t.payment_method)][0] += t.amount
            method_totals[str(t.payment_method)][1] += 1
            if t.requires_manual_review:
                review += 1

        return MonthlyReportResult(
            year_month=year_month,
            total_amount=total,
            transaction_count=len(txns),
            by_category=[
                CategoryAggregate(category=k, total_amount=v[0], count=v[1])
                for k, v in sorted(category_totals.items(), key=lambda kv: -kv[1][0])
            ],
            by_payment_method=[
                CategoryAggregate(category=k, total_amount=v[0], count=v[1])
                for k, v in sorted(method_totals.items(), key=lambda kv: -kv[1][0])
            ],
            review_required_count=review,
        )


def _month_range(year_month: str) -> tuple[datetime, datetime]:
    """``YYYY-MM`` → 해당 월의 [start, end) 앱 시간대 datetime 페어."""
    try:
        year, month = year_month.split("-")
        y, m = int(year), int(month)
    except (ValueError, AttributeError) as exc:
        raise ValueError(f"year_month 는 YYYY-MM 형식이어야 합니다: {year_month}") from exc

    tz = ZoneInfo(get_settings().timezone)
    start = datetime(y, m, 1, tzinfo=tz)
    if m == 12:
        end = datetime(y + 1, 1, 1, tzinfo=tz)
    else:
        end = datetime(y, m + 1, 1, tzinfo=tz)
    # DB 비교는 UTC 로 되든 KST 로 되든 timezone-aware 면 동일하지만 명시적으로
    return start, end
