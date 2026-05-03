# 전역 예외 핸들러 등록 함수
# main.py에서 register_exception_handlers(app) 한 번만 호출하면 됨
#
# 처리 대상:
#   - AppException     → 정의된 status_code + BaseResponse.fail 포맷으로 반환
#   - Exception (기타) → 500 Internal Server Error + BaseResponse.fail 포맷으로 반환

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.common.exception.app_exception import AppException
from app.common.response.base_response import BaseResponse

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """FastAPI 앱에 전역 예외 핸들러를 등록한다."""

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=BaseResponse.fail(exc.message).model_dump(),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content=BaseResponse.fail("Internal server error").model_dump(),
        )
