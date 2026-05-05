# Mailbook Backend — 작업 핸드오프 (2026-05-04)

> 이 문서는 다음 작업 세션에서 컨텍스트를 빠르게 복원하기 위한 진행 기록입니다.
> 전체 설계 청사진은 루트의 `PRD.md`, 아키텍처 규칙은 `CLAUDE.md`를 참조하세요.

---

## ⚠ Phase 1 입력 채널 재정의 (2026-05-04)

PRD 1.3의 "카드사 이메일 결제 알림" 시나리오는 한국 환경에서 비현실적임이 확인되어 **Phase 1 입력 채널을 이메일 가맹점 영수증 only로 재정의**한다.

- 카드사 결제 알림은 SMS / 카드사 앱 푸시 / 토스 등 통합 앱으로 도착, 이메일에는 거의 없음
- 우회 채널 검증: 오픈뱅킹은 핀테크 사업자 계약 필요(개인 불가), 토스페이먼츠는 가맹점용 PG라 용도 부적합, 토스 앱은 외부 API 미제공, iOS는 외부 앱이 SMS 못 읽음
- 따라서 `payment_events.event_type`은 사실상 `MERCHANT_RECEIPT`만 적재됨
- `MatchingEngine`(PR 6) 코드와 `SyncPipeline`의 매칭 호출은 그대로 유지 — 입력에 `CARD_NOTIFICATION`이 없으면 PRD 2.2 Step 2의 "후보 0개" 분기로 자연스럽게 흘러 24h timeout 후 solo transaction으로 확정됨
- 미래에 사업자화 또는 안드로이드 SMS 채널 도입 시 카드사 측 입력이 채워지며 매칭 엔진이 자동 활성화됨. **매칭 관련 코드는 삭제하지 않는다.**

---

## 한눈에 요약

- **PR 0~8 (Phase 1 백엔드 MVP) + PR 5 (Trancy 가맹점 파서) 완료**, `origin/main` (`K-MG-0328/mailbook`, private) 에 push 완료
- **PR 9 완료**: `ResolveSoloTransactions` 에 `force` 옵션 추가 — `/api/v1/transactions/resolve-solo?force=true` 로 24h 컷오프 우회 (검증/관리자 전용)
- 42개 단위 테스트 통과 / `ruff check`, `ruff format`, `mypy app` 모두 통과
- 호스트 PostgreSQL의 `mailbook_backend` DB에 첫 마이그레이션(`fd60fc881b8e_initial_schema`) 적용 완료
- `uv run uvicorn main:app --reload` → http://localhost:8000/docs 로 모든 엔드포인트 확인 가능
- 다음 단계: **실서버 end-to-end 검증** — `.env` 의 `ANTHROPIC_API_KEY` / `GMAIL_OAUTH_*` 채우면 즉시 가능 (아래 절차 참조)

---

## 사용자가 결정한 핵심 사항 (변경 금지)

1. **CLI 생략** — PRD의 `expense-agent sync` 등은 모두 FastAPI 엔드포인트로 대체
2. **4개 도메인 분할** — `email` / `payment_event` / `transaction` / `merchant`
3. **Phase 1은 백엔드만** — 프론트엔드는 Phase 2
4. **Phase 1 입력 채널은 이메일 가맹점 영수증 only** — 카드사 이메일 알림 미도입 (위 재정의 섹션 참조)
5. **PR 5는 첫 가맹점 파서(Trancy)** — 사용자 제공 fixture 기반

---

## PR 진행 상태

| PR | 상태 | 내용 | 관련 테스트 |
|---|---|---|---|
| 0 | ✅ | 의존성 추가 (google-api-python-client, anthropic, rapidfuzz, selectolax, pyyaml), Settings 확장, `infrastructure/external/anthropic_client.py` + `timezone.py`, `.env` 자동 셋업 | — |
| 1 | ✅ | 4개 도메인 ORM (emails, oauth_tokens, payment_events, transactions, processing_runs, merchant_aliases) + alembic `0001_initial` 적용 | — |
| 2 | ✅ | merchant 도메인 4계층 + `config/{merchants,categories}.yaml` 시드 + `/api/v1/merchants/*` | 8개 (alias_resolver, yaml_loaders) |
| 3 | ✅ | email 도메인 4계층 + Gmail OAuth Flow + GmailConnector + Fernet `EncryptedTokenStorage` + `/api/v1/auth/gmail/*`, `/api/v1/emails` | 7개 (gmail connector helpers) |
| 4 | ✅ | payment_event 베이스 (Parser/Registry/ParseResult) + ParsePendingEmails usecase + AnthropicLlmParser (Redis 캐싱) + EmailQueryAdapter/EmailStatusUpdaterAdapter | 7개 (parser_registry, parse_pending_emails) |
| 5 | ✅ | 첫 가맹점 파서 (Trancy) — 사용자 fixture 기반, sender/subject 매칭, HTML→텍스트 fallback | 5개 (test_trancy_parser) |
| 6 | ✅ | transaction 도메인 4계층 + MatchingEngine (PRD 2.2) + Disambiguator + Classifier + ResolveSoloTransactions + RapidFuzzMatcher + AnthropicDisambiguator | 11개 (matching_engine — 모든 분기) |
| 7 | ✅ | SyncPipeline orchestrator + `/api/v1/sync` + Redis lock + EmailFetchPort/EventParsePort anti-corruption | — |
| 8 | ✅ | MonthlyReport + CategoryReport + `/api/v1/reports/{monthly,category}` | — |
| 9 | ✅ | ResolveSoloTransactions `force` 옵션 + `/api/v1/transactions/resolve-solo?force=true` 검증용 우회 채널 | 3개 (test_resolve_solo_transactions) |

---

## 새 가맹점 파서 추가 절차 (PR 5 이후 후속 PR에도 동일)

1. `tests/fixtures/emails/gmail/<가맹점>/` 하위에 `.eml` 파일들 + `expected.json` 저장
2. `app/domains/payment_event/adapter/outbound/parsers/merchant/<가맹점>_parser.py` 작성
   - `Parser` 베이스 상속 (`app/domains/payment_event/domain/service/parser.py`)
   - `name`, `sender_patterns`, `subject_patterns` 클래스 속성으로 정의
   - `can_parse(email) -> bool`: sender + subject 매칭
   - `parse(email) -> ParseResult`:
     - `text = email.body_text or html_to_text(email.body_html)` (`html_text_extractor.html_to_text` 재사용)
     - 본문에서 정규식으로 amount(원 단위 정수), paid_at(KST aware) 추출
     - paid_at은 본문 시각 우선, 없으면 `email.received_at` (Gmail connector가 KST aware로 채워줌)
     - `event_type=EventType.MERCHANT_RECEIPT`, card_company/card_last4는 None (가맹점 영수증)
     - 핵심 필드 누락 시 `ParseResult.fail(parser_name=name, reason=...)`
3. `app/domains/payment_event/adapter/outbound/parsers/provider.py`의 `DEFAULT_PARSERS`에 인스턴스 추가 (등록 순서 = 매칭 우선순위)
4. `config/merchants.yaml`에 가맹점 항목(canonical/aliases/category) 추가
5. `config/parser_routes.yaml`에 운영 가시성용 라우트 추가
6. `tests/domains/payment_event/parsers/test_<가맹점>_parser.py`에 단위 테스트 ≥ 4개 (성공 1+, can_parse 거부 + parse 실패 케이스 3+)

**카드사 파서**: `parsers/card/` 디렉토리는 미래(SMS 채널 도입 등) 대비 보존. 현 Phase 1에서 새 파서 추가 안 함.

**참고할 기존 코드**
- `app/domains/payment_event/adapter/outbound/external/anthropic_llm_parser.py:117` — `EmailLike` 인터페이스 사용 + body_text/body_html fallback 패턴
- `app/domains/payment_event/adapter/outbound/external/html_text_extractor.py:8` — `html_to_text(html: str) -> str`
- `app/infrastructure/external/timezone.py` — `to_app_tz(dt)`, `now_in_app_tz()`
- `tests/domains/payment_event/domain/test_parser_registry.py:22` — `_email()` 헬퍼 패턴
- `app/domains/payment_event/domain/value_object/parse_result.py` — ParseResult 필드 (PRD 2.4)

---

## 환경 셋업 상태

### 호스트 PostgreSQL 사용 중
- 5432 포트는 호스트 PG가 점유 (`postgres` 프로세스 PID 11560)
- `gimmingyu` 계정으로 peer 인증 (비번 없음), DB명 `mailbook_backend`
- Docker `pg-container`도 실행 중이지만 5432 충돌로 호스트 PG가 우선

### `.env` 파일
- `.gitignore`에 포함 (commit 대상 아님)
- 자동 생성된 키:
  - `JWT_SECRET_KEY` (랜덤 hex 64자)
  - `TOKEN_ENCRYPTION_KEY` (Fernet 키)
- **사용자가 직접 채워야 하는 값:**
  - `ANTHROPIC_API_KEY` — LLM 폴백 파서 + matching disambiguator 동작에 필수
  - `GMAIL_OAUTH_CLIENT_ID`, `GMAIL_OAUTH_CLIENT_SECRET` — Gmail OAuth 동작에 필수 (Google Cloud Console에서 OAuth 2.0 Client 발급)

### 시드 데이터
- `config/categories.yaml` — PRD 8.4의 9개 카테고리
- `config/merchants.yaml` — 5개 가맹점 시드 (쿠팡, 스타벅스, 배달의민족, 넷플릭스, 카카오T)
- `config/card_companies.yaml`, `config/parser_routes.yaml` — 빈 골격 (PR 5에서 채움)
- 시드 적재 명령: `curl -X POST http://localhost:8000/api/v1/merchants/seed`

---

## 등록된 엔드포인트

```
GET    /api/v1/health
GET    /api/v1/auth/gmail/start              — OAuth URL 발급
GET    /api/v1/auth/gmail/callback           — OAuth 콜백 (브라우저 redirect)
GET    /api/v1/emails                         — 메일 조회 (status 필터)
GET    /api/v1/merchants/categories           — 카테고리 목록
GET    /api/v1/merchants/aliases              — 가맹점 알리아스 목록
POST   /api/v1/merchants/aliases              — 수동 알리아스 학습
POST   /api/v1/merchants/seed                 — yaml 시드 적재
GET    /api/v1/payment-events                 — 파싱된 이벤트 목록 (matched 필터)
POST   /api/v1/payment-events/parse           — pending 메일 파싱 단독 실행
GET    /api/v1/transactions                   — 거래 목록
GET    /api/v1/transactions/review            — 수동 검토 필요 거래
POST   /api/v1/transactions/match             — 매칭 단독 실행
POST   /api/v1/transactions/resolve-solo      — 24h timeout solo 처리
POST   /api/v1/transactions/{id}/verify       — 거래 검증
POST   /api/v1/sync                            — 전체 파이프라인 (fetch→parse→match→solo)
GET    /api/v1/reports/monthly?year_month=YYYY-MM
GET    /api/v1/reports/category?year_month=YYYY-MM
```

---

## 도메인 ↔ PRD 모듈 매핑

| PRD 모듈 | 매핑 위치 |
|---|---|
| `connectors` | `email/adapter/outbound/external/gmail_connector.py` |
| `parsers` 베이스 | `payment_event/domain/service/parser.py` + `parser_registry.py` |
| `parsers` 구체 | `payment_event/adapter/outbound/parsers/{card,merchant}/` (PR 5에서 채움) |
| `parsers` LLM 폴백 | `payment_event/adapter/outbound/external/anthropic_llm_parser.py` |
| `matcher` | `transaction/domain/service/matching_engine.py` (PRD 2.2 Step 1~3) + `disambiguator.py` |
| `classifier` | `transaction/domain/service/classifier.py` |
| `reports` | `transaction/application/usecase/{monthly,category}_report.py` |
| `orchestrator` | `transaction/application/usecase/sync_pipeline.py` (★ 4개 도메인 anti-corruption 포트로 조율) |
| `merchant_aliases` | `merchant/` 도메인 + `config/merchants.yaml` 시드 |

---

## 핵심 결정 사항 (코드와 함께 영구 보존)

1. **Orchestrator는 transaction 도메인** — transaction이 최종 산출물이고 다른 3개 도메인 조율
2. **Anti-corruption 포트 패턴** — payment_event가 email을 호출하거나, transaction이 payment_event/merchant를 호출할 때 자체 포트 정의 + 호출되는 도메인의 outbound `orchestration/` 디렉토리에 wrapper 어댑터 구현
3. **Anthropic SDK 분리** — `infrastructure/external/anthropic_client.py`에 sanitizer만 공용, 도메인-특화 호출(파서 폴백 vs disambiguator)은 각 도메인 outbound에서 독립 구현 (프롬프트/스키마가 다름)
4. **OAuth 토큰** — Fernet 대칭키 암호화 후 `oauth_tokens` 테이블에 저장. 키는 `TOKEN_ENCRYPTION_KEY` 환경변수 (운영은 Phase 2에서 KMS)
5. **단일 사용자 가정** — 모든 도메인 ORM에 `user_id` nullable 컬럼 미리 포함 (Phase 2 마이그레이션 부담 감소). `OWNER_USER_ID=1` 환경변수로 고정
6. **LLM 캐싱** — Redis 24h, key는 `sha256(sender + subject + body[:4096])`. 동일 message_id 재호출은 `parsed_status`로 차단
7. **단계별 commit** — `SyncPipeline`은 한 session 내에서 단계 끝마다 commit해 transaction 분리 (긴 트랜잭션 idle 타임아웃 회피)
8. **sync 동시 실행 차단** — Redis `SET sync_lock NX EX 600`

---

## 도메인 디렉토리 구조 (실제 트리)

```
app/domains/
├── email/
│   ├── domain/
│   │   ├── entity/email.py
│   │   ├── value_object/{parsed_status,email_source,oauth_token}.py
│   │   └── service/  (현재 비어있음 — email_dedup_service는 미구현)
│   ├── application/
│   │   ├── port/{email_repository,email_connector,oauth_token_storage}_port.py
│   │   ├── usecase/{fetch_emails,start_oauth,complete_oauth}.py
│   │   ├── request/fetch_emails_request.py
│   │   └── response/{email_response,oauth_url_response}.py
│   ├── adapter/
│   │   ├── inbound/api/email_router.py
│   │   └── outbound/
│   │       ├── persistence/{email_repository,encrypted_token_storage}.py
│   │       ├── external/{gmail_connector,google_oauth_flow}.py
│   │       └── orchestration/{email_query_adapter,email_status_updater_adapter,email_fetch_adapter}.py
│   └── infrastructure/
│       ├── orm/email_orm.py  (EmailORM + OAuthTokenORM)
│       └── mapper/{email_mapper,oauth_token_mapper}.py
│
├── payment_event/
│   ├── domain/
│   │   ├── entity/payment_event.py
│   │   ├── value_object/{event_type,parse_result,money}.py
│   │   └── service/{parser,parser_registry}.py
│   ├── application/
│   │   ├── port/{payment_event_repository,llm_parser,parser_provider,email_query,email_status_updater}_port.py
│   │   ├── usecase/parse_pending_emails.py
│   │   ├── request/pending_email.py
│   │   └── response/payment_event_response.py
│   ├── adapter/
│   │   ├── inbound/api/payment_event_router.py
│   │   └── outbound/
│   │       ├── persistence/payment_event_repository.py
│   │       ├── external/{anthropic_llm_parser,html_text_extractor}.py
│   │       ├── parsers/{provider,yaml_routing,card/__init__.py,merchant/__init__.py}
│   │       └── orchestration/event_parse_adapter.py
│   └── infrastructure/
│       ├── orm/payment_event_orm.py
│       ├── mapper/payment_event_mapper.py
│       └── yaml_loader/card_companies_loader.py
│
├── transaction/
│   ├── domain/
│   │   ├── entity/{transaction,processing_run}.py
│   │   ├── value_object/{payment_method,match_decision}.py
│   │   └── service/{matching_engine,classifier}.py  (disambiguator는 matching_engine에 통합)
│   ├── application/
│   │   ├── port/{transaction_repository,processing_run_repository,payment_event_query,merchant_resolver,llm_disambiguator,fuzzy_matcher,email_fetch,event_parse}_port.py
│   │   ├── usecase/{match_unmatched_events,resolve_solo_transactions,list_transactions,verify_transaction,sync_pipeline,monthly_report,category_report}.py
│   │   ├── request/verify_request.py
│   │   └── response/{transaction_response,report_response}.py
│   ├── adapter/
│   │   ├── inbound/api/{transaction_router,sync_router,report_router}.py
│   │   └── outbound/
│   │       ├── persistence/{transaction_repository,processing_run_repository,payment_event_query_adapter,merchant_resolver_adapter}.py
│   │       └── external/{rapidfuzz_matcher,anthropic_disambiguator}.py
│   └── infrastructure/
│       ├── orm/transaction_orm.py  (TransactionORM + ProcessingRunORM)
│       └── mapper/{transaction_mapper,processing_run_mapper}.py
│
└── merchant/
    ├── domain/
    │   ├── entity/merchant_alias.py
    │   ├── value_object/{category,learned_from}.py
    │   └── service/alias_resolver.py
    ├── application/
    │   ├── port/{merchant_alias_repository,category_catalog}_port.py
    │   ├── usecase/{seed_from_yaml,resolve_canonical,learn_alias,list_aliases}.py
    │   ├── request/{learn_alias_request,merchant_seed_row}.py
    │   └── response/{alias_response,category_response}.py
    ├── adapter/
    │   ├── inbound/api/merchant_router.py
    │   └── outbound/persistence/merchant_alias_repository.py
    └── infrastructure/
        ├── orm/merchant_alias_orm.py
        ├── mapper/merchant_alias_mapper.py
        └── yaml_loader/{merchants_yaml_loader,categories_yaml_loader}.py
```

---

## 실서버 end-to-end 검증 절차

### 사전 준비 (사용자 직접 수행)

1. **Google OAuth 2.0 Client 발급** — https://console.cloud.google.com
   - Gmail API enable
   - OAuth consent screen → External, scope `gmail.readonly`, 본인 이메일을 Test User 로 등록
   - Credentials → OAuth Client ID (Web application) 생성, Authorized redirect URI: `http://localhost:8000/api/v1/auth/gmail/callback`
   - `.env` 에 기록:
     ```
     GMAIL_OAUTH_CLIENT_ID=<...>.apps.googleusercontent.com
     GMAIL_OAUTH_CLIENT_SECRET=<...>
     GMAIL_OAUTH_REDIRECT_URI=http://localhost:8000/api/v1/auth/gmail/callback
     ```
2. **Anthropic API Key 발급** — https://console.anthropic.com → API Keys → Create Key
   - `.env` 에 `ANTHROPIC_API_KEY=sk-ant-...`
3. Redis / PostgreSQL 동작 확인 + `uv run alembic upgrade head`

### 검증 단계

```bash
# 1. 서버 띄우기
uv run uvicorn main:app --reload --port 8000

# 2. 시드 적재 (한 번만)
curl -X POST http://localhost:8000/api/v1/merchants/seed

# 3. OAuth 로그인 — 응답의 auth_url 을 브라우저로 열어 본인 Gmail 로그인
curl http://localhost:8000/api/v1/auth/gmail/start

# 4. 메일 동기화 (fetch → parse → match → solo)
curl -X POST http://localhost:8000/api/v1/sync

# 5. 검증
curl 'http://localhost:8000/api/v1/emails?status=parsed'             # Trancy 메일 1건
curl 'http://localhost:8000/api/v1/payment-events?matched=false'     # parser_name="trancy"
curl -X POST 'http://localhost:8000/api/v1/transactions/resolve-solo?force=true'  # 즉시 solo 처리 (검증용)
curl http://localhost:8000/api/v1/transactions                        # Trancy 거래 확인
```

> `force=true` 는 24h 타임아웃을 우회하는 검증/관리자 전용 채널이다. 운영 흐름(`/api/v1/sync` 내부) 은 여전히 24h 컷오프를 따른다.

---

## 다음 세션 시작 체크리스트

```bash
# 1. 환경 확인
cd /Users/gimmingyu/Documents/GitHub/Mailbook/Mailbook-backend
psql -h localhost -d mailbook_backend -c "\dt"   # 6개 테이블 확인
docker ps | grep -E "pg-container|redis-container"

# 2. 의존성/마이그레이션 확인
uv sync
uv run alembic current   # fd60fc881b8e (head) 여야 함

# 3. 테스트
uv run ruff check . && uv run mypy app && uv run pytest -v   # 42 passed

# 4. 서버 띄워 동작 확인
uv run uvicorn main:app --reload --port 8000
# http://localhost:8000/docs

# 5. 시드 적재 (한 번만)
curl -X POST http://localhost:8000/api/v1/merchants/seed
```

---

## 위험 / 오픈 이슈

- **`force=true` 는 검증/관리자 전용** — Phase 2 인증 도입 시 admin 전용으로 제한 검토. 운영 SyncPipeline 호출부는 여전히 24h 컷오프 사용
- **alembic autogenerate가 KST timezone-aware DateTime을 정확히 인식하는지**는 1차 확인 완료 (`DateTime(timezone=True)` + `server_default=func.now()` 정상 적용)
- **`sync_pipeline.py`에 lambda type alias 사용** — 추후 별도 ProcessingRunRepositoryPort에 의존하도록 리팩터 가능 (현재는 Callable 직접 사용)
- **Phase 2 사용자 도메인 도입 시**: 모든 `user_id` nullable → not null 마이그레이션 + JWT 미들웨어 추가 필요
- **`AnthropicLlmParser._cache_key`가 4096 바이트만 사용** — 매우 긴 메일에서 충돌 가능성 약간 있음 (Phase 2에서 본문 hash 전체로 변경 검토)

---

## 참고 자료 위치

- 전체 설계: `/Users/gimmingyu/Documents/GitHub/Mailbook/PRD.md`
- 백엔드 아키텍처 규칙: `Mailbook-backend/CLAUDE.md`
- 프론트엔드 (Phase 2): `Mailbook-frontend/CLAUDE.md`
- 원본 plan: `/Users/gimmingyu/.claude/plans/prd-md-giggly-phoenix.md`
