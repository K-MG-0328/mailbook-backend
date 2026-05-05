from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response.base_response import BaseResponse
from app.domains.transaction.adapter.outbound.persistence.transaction_repository import (
    TransactionRepository,
)
from app.domains.transaction.application.response.report_response import (
    CategoryReportResponse,
    MonthlyReportResponse,
)
from app.domains.transaction.application.usecase.category_report import CategoryReport
from app.domains.transaction.application.usecase.monthly_report import MonthlyReport
from app.infrastructure.config.settings import get_settings
from app.infrastructure.database.database import get_db

router = APIRouter(prefix="/reports", tags=["reports"])

SessionDep = Annotated[AsyncSession, Depends(get_db)]
YearMonthQuery = Annotated[str, Query(pattern=r"^\d{4}-\d{2}$", description="YYYY-MM")]


@router.get("/monthly", response_model=BaseResponse[MonthlyReportResponse])
async def monthly_report_endpoint(
    session: SessionDep, year_month: YearMonthQuery
) -> BaseResponse[MonthlyReportResponse]:
    settings = get_settings()
    result = await MonthlyReport(TransactionRepository(session)).execute(
        user_id=settings.owner_user_id, year_month=year_month
    )
    return BaseResponse.ok(data=MonthlyReportResponse.from_result(result))


@router.get("/category", response_model=BaseResponse[CategoryReportResponse])
async def category_report_endpoint(
    session: SessionDep, year_month: YearMonthQuery
) -> BaseResponse[CategoryReportResponse]:
    settings = get_settings()
    result = await CategoryReport(TransactionRepository(session)).execute(
        user_id=settings.owner_user_id, year_month=year_month
    )
    return BaseResponse.ok(data=CategoryReportResponse.from_result(result))
