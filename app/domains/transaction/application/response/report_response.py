from __future__ import annotations

from pydantic import BaseModel

from app.domains.transaction.application.usecase.category_report import (
    CategoryReportResult,
    MerchantBreakdown,
)
from app.domains.transaction.application.usecase.monthly_report import (
    CategoryAggregate,
    MonthlyReportResult,
)


class CategoryAggregateResponse(BaseModel):
    category: str
    total_amount: int
    count: int

    @classmethod
    def from_dto(cls, dto: CategoryAggregate) -> "CategoryAggregateResponse":
        return cls(category=dto.category, total_amount=dto.total_amount, count=dto.count)


class MonthlyReportResponse(BaseModel):
    year_month: str
    total_amount: int
    transaction_count: int
    by_category: list[CategoryAggregateResponse]
    by_payment_method: list[CategoryAggregateResponse]
    review_required_count: int

    @classmethod
    def from_result(cls, result: MonthlyReportResult) -> "MonthlyReportResponse":
        return cls(
            year_month=result.year_month,
            total_amount=result.total_amount,
            transaction_count=result.transaction_count,
            by_category=[CategoryAggregateResponse.from_dto(c) for c in result.by_category],
            by_payment_method=[
                CategoryAggregateResponse.from_dto(p) for p in result.by_payment_method
            ],
            review_required_count=result.review_required_count,
        )


class MerchantBreakdownResponse(BaseModel):
    canonical_merchant: str
    total_amount: int
    count: int

    @classmethod
    def from_dto(cls, dto: MerchantBreakdown) -> "MerchantBreakdownResponse":
        return cls(
            canonical_merchant=dto.canonical_merchant,
            total_amount=dto.total_amount,
            count=dto.count,
        )


class CategoryDetailResponse(BaseModel):
    category: str
    total_amount: int
    count: int
    merchants: list[MerchantBreakdownResponse]


class CategoryReportResponse(BaseModel):
    year_month: str
    categories: list[CategoryDetailResponse]

    @classmethod
    def from_result(cls, result: CategoryReportResult) -> "CategoryReportResponse":
        return cls(
            year_month=result.year_month,
            categories=[
                CategoryDetailResponse(
                    category=c.category,
                    total_amount=c.total_amount,
                    count=c.count,
                    merchants=[MerchantBreakdownResponse.from_dto(m) for m in c.merchants],
                )
                for c in result.categories
            ],
        )
