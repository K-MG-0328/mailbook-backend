import asyncio
import logging
import sys
from contextlib import asynccontextmanager

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.adapter.inbound.api.v1_router import api_v1_router
from app.common.exception.global_exception_handler import register_exception_handlers
from app.infrastructure.cache.redis_client import redis_client
from app.infrastructure.config.logging_config import setup_logging
from app.infrastructure.config.settings import Settings, get_settings
from app.infrastructure.database.database import check_db_health, engine

settings: Settings = get_settings()
setup_logging(settings.log_level)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI):
    if not await check_db_health():
        logger.warning(
            "PostgreSQL 연결 실패 — 인프라가 아직 준비 안 된 상태에서도 서버는 부팅을 계속한다. "
            "도메인 라우터 추가 시 DB 미가용은 라우터 단에서 적절히 처리할 것."
        )
    try:
        yield
    finally:
        await redis_client.aclose()
        await engine.dispose()


app = FastAPI(debug=settings.debug, lifespan=lifespan, title="Mailbook Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.cors_allowed_frontend_url],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Cookie", "Set-Cookie"],
)

app.include_router(api_v1_router)
register_exception_handlers(app)


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Mailbook Backend"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
