"""pytest 공통 fixture.

Settings 환경변수가 누락된 상태에서 import만으로 fail하지 않도록 import 시점에
필수 env를 주입한다. 실제 통합 테스트는 docker compose의 postgres/redis가 떠 있어야 동작.
"""

import os

# Settings BaseSettings는 import 시점에 환경변수를 읽는다. 테스트 환경 기본값 주입.
os.environ.setdefault("POSTGRES_USER", "postgres")
os.environ.setdefault("POSTGRES_PASSWORD", "changeme")
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_PORT", "5432")
os.environ.setdefault("POSTGRES_DB", "mailbook_backend_test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-not-for-production")
os.environ.setdefault("OPENAI_API_KEY", "sk-test-not-real")

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """FastAPI 앱을 in-memory ASGI transport로 호출하는 AsyncClient. DB/Redis 불필요."""
    from main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
