from fastapi import APIRouter

from app.common.response.base_response import BaseResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=BaseResponse[dict[str, str]])
async def health_check() -> BaseResponse[dict[str, str]]:
    """단순 헬스체크. 프론트엔드 ↔ 백엔드 왕복 확인용."""
    return BaseResponse.ok(data={"status": "ok"})
