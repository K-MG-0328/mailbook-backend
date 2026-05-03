# /api/v1 공통 라우터 집합
# 새 도메인 라우터를 만들면 이 파일에 include_router만 추가한다.
#
# 추가 예시:
#   from app.domains.prompt.adapter.inbound.api.prompt_router import router as prompt_router
#   api_v1_router.include_router(prompt_router)

from fastapi import APIRouter

from app.adapter.inbound.api.health_router import router as health_router

api_v1_router = APIRouter(prefix="/api/v1")

# --- 도메인 라우터 등록 ---
api_v1_router.include_router(health_router)
