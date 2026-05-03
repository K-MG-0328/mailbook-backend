# Mailbook Backend

Mailbook 프로젝트의 백엔드. Python 3.13 + FastAPI + SQLAlchemy(async) + PostgreSQL + Redis + Alembic 기반의 4-layer(Hexagonal/DDD) 구성.

## 스택

- **FastAPI** + uvicorn[standard] · ASGI lifespan + CORS + 글로벌 예외 핸들러
- **SQLAlchemy 2.0 async** + asyncpg · `get_db()` 패턴, 풀링/헬스체크 내장
- **Redis (asyncio)** singleton + `get_redis()`
- **Alembic** async 마이그레이션 (`alembic/env.py`)
- **Pydantic BaseSettings** + `@lru_cache` 싱글톤 (`infrastructure/config/settings.py`)
- **JWT 토큰** 의존성 (`python-jose[cryptography]`)
- **공통 응답 스키마** `BaseResponse[T]` (`.ok()` / `.fail()` 헬퍼)
- **커스텀 예외** `AppException` + 글로벌 핸들러
- **로깅** 콘솔 + 일일 로테이션 파일 + extra fields formatter + httpx 로그 마스킹
- **4-layer 디렉토리 구조** — domain / application / adapter / infrastructure
- Ruff (lint+format) · mypy (strict) · pytest (asyncio) · pre-commit
- Dockerfile (uv multi-stage) · docker-compose (postgres + redis)
- GitHub Actions CI (ruff + mypy + pytest + alembic smoke)

## 시작하기

```bash
uv sync                              # 의존성 설치
cp .env.example .env                 # 비밀 값 채워넣기
docker compose up -d postgres redis  # 인프라 기동
make migrate                         # alembic upgrade head
make dev                             # http://localhost:8000
```

헬스체크:

```bash
curl http://localhost:8000/api/v1/health
# → {"success":true,"message":"success","data":{"status":"ok"}}
```

## 디렉토리 구조

```
.
├── main.py                      # FastAPI 부트스트랩 (lifespan / CORS / 예외 핸들러)
├── pyproject.toml               # 의존성 + ruff/mypy/pytest 설정
├── alembic/                     # DB 마이그레이션 (async)
├── docker-compose.yml           # postgres + redis (+ fastapi)
├── Dockerfile                   # uv multi-stage build
├── Makefile                     # dev/test/lint/migrate/up/down 단축 명령
├── CLAUDE.md                    # 아키텍처 규칙 (도메인 추가 시 반드시 읽기)
├── tests/                       # pytest + AsyncClient
└── app/
    ├── adapter/inbound/api/     # 공통 라우터 (health, v1_router)
    ├── common/                  # exception, response (BaseResponse)
    ├── domains/                 # 도메인별 4계층 코드
    │   └── <domain>/
    │       ├── domain/          # Entity, Value Object, Domain Service
    │       ├── application/     # UseCase, Port, Request/Response DTO
    │       ├── adapter/         # Inbound (api), Outbound (persistence/external)
    │       └── infrastructure/  # ORM, Mapper
    └── infrastructure/
        ├── config/              # Settings (BaseSettings) + logging
        ├── database/            # async engine, get_db()
        └── cache/               # Redis singleton
```

새 도메인 작성 단계는 [`CLAUDE.md`의 "새 도메인 만들기"](./CLAUDE.md#새-도메인-만들기--단계별-가이드) 참고.

## 스크립트 (`make help`)

```bash
make install         # uv sync
make dev             # uvicorn 개발 서버 (--reload)
make test            # pytest
make lint            # ruff check + format check
make fmt             # ruff format + autofix
make typecheck       # mypy app
make migrate         # alembic upgrade head
make migration MSG="..." # alembic revision --autogenerate
make up / make down  # docker compose postgres+redis
make logs            # docker compose logs -f
```

## 아키텍처

- **Hexagonal (Ports & Adapters) + DDD** 4계층
- 의존성 방향: Adapter → Application → Domain. Infrastructure는 Adapter/Application에서만 사용
- **Domain 레이어는 외부(FastAPI/SQLAlchemy/Redis/Pydantic 등) import 금지** — 순수 Python

전체 규칙은 [`CLAUDE.md`](./CLAUDE.md) 참고.
