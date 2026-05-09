# Mailbook Backend

> 이메일 영수증과 카드 결제 알림을 자동으로 매칭해 **PG 중복 없는 단일 가계부**를 만들어 주는 서비스의 백엔드.
>
> Python 3.13 · FastAPI · SQLAlchemy 2 (async) · PostgreSQL · Redis · Alembic 기반 **Hexagonal + DDD** 4-layer.

관련 레포: 프론트엔드는 [`mailbook-frontend`](https://github.com/K-MG-0328/mailbook-frontend) 참고.

## 무엇을 하나

1. Gmail 등에서 결제 관련 이메일을 가져온다.
2. 가맹점 영수증 (`merchant_receipt`) 과 카드사 알림 (`card_notification`) 을 룰 기반 파서 → 실패 시 LLM 폴백으로 파싱한다.
3. 같은 결제 1건의 영수증 + 카드 알림을 **±10분 / 동일 금액 / 카드 끝자리 / 가맹점명 fuzzy** 로 매칭해 1건의 거래로 통합한다.
4. 24시간 안에 짝을 못 찾은 이벤트는 단독 거래로 fallback (정기결제 추정 등).
5. `transactions` 테이블이 사용자의 가계부.

상세 설계는 루트의 `PRD.md` 와 [`CLAUDE.md`](./CLAUDE.md) 의 아키텍처 규칙 참고.

## 주요 기능

- **다중 파서 라우팅**: 가맹점별 룰 기반 파서 (현 Trancy, Anthropic) → 매칭 실패 시 Claude 모델 호출 → 1회 retry 후 `failed`
- **PG 중복 해소**: 영수증/카드 알림을 단일 거래로 합쳐 가계부 중복 제거
- **다중 이메일 계정**: `(source, account, message_id)` 유니크. Gmail 다계정 동시 처리
- **다중 통화**: `currency` 컬럼으로 KRW / USD 분리 저장 (USD 는 cents 단위)
- **카테고리 학습**: `merchant_aliases` 로 가맹점명 정규화 + 카테고리 분류 (YAML 시드 + 학습 누적)
- **월별/카테고리별 리포트** (`/transactions/reports/...`)
- **동시 sync 차단**: Redis NX 락 (`mailbook:sync_lock`)
- **OAuth 토큰 암호화 저장** (Fernet)

## 기술 스택

- **FastAPI** + uvicorn[standard] · ASGI lifespan + CORS + 글로벌 예외 핸들러
- **SQLAlchemy 2.0 (async)** + asyncpg · `get_db()` 풀링/헬스체크
- **Redis (asyncio)** · 동시성 락, LLM 응답 캐시
- **Alembic** async 마이그레이션
- **Pydantic Settings** · `@lru_cache` 싱글톤 (`infrastructure/config/settings.py`)
- **Anthropic SDK** · LLM 파싱/매칭 disambiguation
- **Google API client** · Gmail 메일 fetch
- **rapidfuzz** · 가맹점명 fuzzy 매칭, **selectolax** · HTML 본문 추출
- **JWT** · `python-jose[cryptography]`
- **Ruff + mypy(strict) + pytest(asyncio) + pre-commit**
- **Docker** · uv multi-stage Dockerfile, docker-compose (postgres + redis)
- **GitHub Actions CI** · ruff + mypy + pytest + alembic smoke

## 시작하기

```bash
uv sync                               # 의존성 설치 (Python 3.13 필요)
cp .env.example .env                  # 비밀 값 채우기 (아래 참고)
docker compose up -d postgres redis   # 로컬 인프라 기동
make migrate                          # alembic upgrade head
make dev                              # http://localhost:8000 (또는 PORT 값)
```

헬스체크:

```bash
curl http://localhost:8000/api/v1/health
# → {"success":true,"message":"success","data":{"status":"ok"}}
```

### 필수 환경 변수 (`.env.example` 의 핵심)

| 키 | 설명 |
| --- | --- |
| `POSTGRES_*` | DB 접속 정보 (host/port/user/password/db) |
| `REDIS_HOST`, `REDIS_PORT` | Redis 접속 정보 |
| `JWT_SECRET_KEY` | 32바이트+ 임의값. `openssl rand -hex 32` |
| `TOKEN_ENCRYPTION_KEY` | OAuth 토큰 암호화용 Fernet 키. `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| `ANTHROPIC_API_KEY` | LLM 폴백 파서 + 매칭 disambiguation |
| `GMAIL_OAUTH_CLIENT_ID`, `GMAIL_OAUTH_CLIENT_SECRET`, `GMAIL_OAUTH_REDIRECT_URI` | Gmail 연동 (Google Cloud Console 발급) |
| `CORS_ALLOWED_FRONTEND_URL` | 프론트엔드 origin |

전체 목록은 [`.env.example`](./.env.example).

## 디렉토리 구조

```
.
├── main.py                     # FastAPI 부트스트랩 (lifespan / CORS / 예외 핸들러)
├── pyproject.toml              # 의존성 + ruff/mypy/pytest 설정
├── alembic/                    # async 마이그레이션
├── docker-compose.yml          # postgres + redis (+ fastapi)
├── Dockerfile                  # uv multi-stage build
├── Makefile                    # dev/test/lint/migrate/up/down 단축 명령
├── CLAUDE.md                   # 아키텍처 규칙 (도메인 추가 시 필수 참고)
├── tests/                      # pytest + AsyncClient
└── app/
    ├── adapter/inbound/api/    # 공통 라우터 (health, v1_router)
    ├── common/                 # 글로벌 예외, BaseResponse[T]
    ├── domains/
    │   ├── email/              # Gmail/메일 fetch + 상태 관리
    │   ├── payment_event/      # 영수증/카드알림 파싱, LLM 폴백
    │   ├── merchant/           # 가맹점 정규화/카테고리 (YAML 시드 + 학습)
    │   └── transaction/        # 매칭/단독거래/리포트
    └── infrastructure/
        ├── config/             # Pydantic Settings + 로깅
        ├── database/           # async engine, get_db()
        ├── cache/              # Redis singleton
        └── external/           # 시간대 등 공통 외부 헬퍼
```

각 도메인은 `domain / application / adapter / infrastructure` 4계층을 따른다 ([`CLAUDE.md`](./CLAUDE.md)).

## 주요 API (v1)

| 경로 | 용도 |
| --- | --- |
| `GET /api/v1/health` | 헬스체크 |
| `POST /api/v1/sync` | 메일 fetch → 파싱 → 매칭까지 한번에 |
| `GET /api/v1/transactions` | 거래 목록 (가계부) |
| `GET /api/v1/transactions/reports/monthly` | 월별 리포트 |
| `GET /api/v1/transactions/reports/categories` | 카테고리 리포트 |
| `GET /api/v1/payment-events` | 파싱된 결제 이벤트 |
| `GET /api/v1/emails` | 원본 이메일 목록 |
| `GET /api/v1/merchants` | 가맹점 별칭 |

상세 시그니처는 `/docs` (FastAPI 자동 문서) 또는 각 도메인의 `adapter/inbound/api/*_router.py`.

## 개발 명령 (`make help`)

```bash
make install          # uv sync
make dev              # uvicorn --reload
make test             # pytest -v
make lint             # ruff check + format check
make fmt              # ruff format + autofix
make typecheck        # mypy app
make migrate          # alembic upgrade head
make migration MSG="..." # 마이그레이션 신규 생성
make up / make down   # docker compose postgres+redis
make logs             # docker compose logs -f
```

## 아키텍처 핵심 규칙

- **Hexagonal (Ports & Adapters) + DDD** 4계층
- 의존성 방향: `Adapter → Application → Domain`. Infrastructure 는 Adapter/Application 에서만 사용
- **Domain 레이어는 외부 import 금지** (FastAPI / SQLAlchemy / Redis / Pydantic / HTTP 클라이언트 모두 X) — 순수 Python
- ORM Model 과 Domain Entity 는 분리. Mapper 가 양방향 변환 담당
- Request / Response DTO 는 Application 레이어. Domain Entity 를 직접 응답하지 않는다

전체 규칙·새 도메인 추가 가이드는 [`CLAUDE.md`](./CLAUDE.md).

## 라이선스

[MIT](./LICENSE).
