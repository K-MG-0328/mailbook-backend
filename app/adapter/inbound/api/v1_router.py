# /api/v1 공통 라우터 집합
# 새 도메인 라우터를 만들면 이 파일에 include_router만 추가한다.
#
# 추가 예시:
#   from app.domains.prompt.adapter.inbound.api.prompt_router import router as prompt_router
#   api_v1_router.include_router(prompt_router)

from fastapi import APIRouter

from app.adapter.inbound.api.health_router import router as health_router
from app.domains.email.adapter.inbound.api.email_router import router as email_router
from app.domains.merchant.adapter.inbound.api.merchant_router import router as merchant_router
from app.domains.payment_event.adapter.inbound.api.payment_event_router import (
    router as payment_event_router,
)
from app.domains.transaction.adapter.inbound.api.report_router import router as report_router
from app.domains.transaction.adapter.inbound.api.sync_router import router as sync_router
from app.domains.transaction.adapter.inbound.api.transaction_router import (
    router as transaction_router,
)

api_v1_router = APIRouter(prefix="/api/v1")

# --- 도메인 라우터 등록 ---
api_v1_router.include_router(health_router)
api_v1_router.include_router(merchant_router)
api_v1_router.include_router(email_router)
api_v1_router.include_router(payment_event_router)
api_v1_router.include_router(transaction_router)
api_v1_router.include_router(sync_router)
api_v1_router.include_router(report_router)
