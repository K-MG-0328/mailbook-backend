# CLAUDE.md

이 파일은 Claude Code(claude.ai/code) 및 새 도메인 코드를 작성하는 모든 기여자에게 아키텍처 규칙을 전달한다.

## 프로젝트 개요

Mailbook 백엔드. **FastAPI 기반 Hexagonal Architecture + Domain Driven Design (DDD)** 구조를 따르는 Python 서비스이며 `backend-starter` 템플릿에서 출발했다.

## Commands

- **Run dev server**: `uvicorn main:app --reload --host 0.0.0.0 --port 8000`
- **Run directly**: `python main.py` (포트 8000으로 실행)
- **Lint/Format**: `ruff check . && ruff format .`
- **Type check**: `mypy app`
- **Test**: `pytest -v`
- **DB migration**: `alembic upgrade head` (모델 추가 시 `alembic revision --autogenerate -m "..."`)

## 목적

이 문서의 목적은 다음과 같다.

- AI가 코드를 생성할 때 아키텍처 규칙을 위반하지 않도록 강제
- Domain, Application, Adapter, Infrastructure 레이어의 명확한 역할 분리
- ORM, Redis, External API, Environment 설정 등의 올바른 위치 규정
- 유지보수성과 확장성을 고려한 일관된 코드 구조 유지

이 문서에 정의된 규칙은 항상 준수되어야 한다.

---

# 프로젝트 구조

프로젝트는 다음과 같은 디렉토리 구조를 따른다.

```
app
 ├ domains
 │   └ <domain_name>
 │       ├ domain
 │       │   ├ entity
 │       │   ├ value_object
 │       │   └ service
 │       │
 │       ├ application
 │       │   ├ usecase
 │       │   ├ port           ← Repository Port (ABC/Protocol)
 │       │   ├ request
 │       │   └ response
 │       │
 │       ├ adapter
 │       │   ├ inbound
 │       │   │   └ api
 │       │   │
 │       │   └ outbound
 │       │       ├ persistence
 │       │       └ external
 │       │
 │       └ infrastructure
 │           ├ orm
 │           └ mapper
 │
 ├ infrastructure
 │   ├ config
 │   ├ database
 │   ├ cache
 │   └ external
 │
 └ main.py
```

---

# 아키텍처 원칙

이 프로젝트는 **Hexagonal Architecture (Ports and Adapters)** 를 따른다.

레이어 의존성 방향은 다음과 같다.

```
Adapter → Application → Domain
Infrastructure → Adapter / Application
```

의존성은 항상 **안쪽 레이어 방향으로만 흐른다.**

---

# Domain Layer 규칙

Domain 레이어는 **비즈니스 로직의 핵심**이다.

Domain에는 다음만 포함될 수 있다.

- Entity
- Value Object
- Domain Service
- Domain Business Rule

## Domain Layer MUST 규칙

Domain 레이어는 다음을 **절대 import하면 안 된다.**

- FastAPI
- SQLAlchemy
- Redis
- Pydantic
- HTTP Client
- External API
- Environment 설정
- ORM Model

Domain 코드는 **순수 Python 코드**여야 한다.

---

# Application Layer 규칙

Application 레이어는 **UseCase를 정의하는 레이어**이다.

Application 레이어의 역할

- UseCase 실행
- Domain Entity 조합
- Repository Port 호출
- Request / Response DTO 정의

## Application Layer MUST 규칙

Application 레이어는 다음을 **직접 사용하면 안 된다.**

- FastAPI
- SQLAlchemy ORM
- Redis
- External API Client

외부 시스템 접근은 **Port 또는 Adapter를 통해서만 접근해야 한다.**

---

# Request / Response DTO 규칙

API 입력과 출력은 **Domain Entity와 반드시 분리해야 한다.**

Request / Response DTO는 **Application Layer에 위치해야 한다.**

## MUST 규칙

Domain Entity를 **API Response로 직접 반환하면 안 된다.** 항상 DTO를 사용해야 한다.

---

# Adapter Layer 규칙

Adapter 레이어는 **외부 인터페이스와 Application 사이를 연결하는 역할**을 한다.

## Inbound Adapter

외부 요청을 Application으로 전달한다. (FastAPI Router, REST endpoint)

위치: `adapter/inbound/api`

## Outbound Adapter

Application이 외부 시스템을 사용할 수 있도록 구현한다. (Repository 구현, External API Client, Cache Adapter)

위치: `adapter/outbound`

---

# Infrastructure Layer 규칙

Infrastructure 레이어는 **기술적인 구현 요소**를 포함한다.

- Database Session, ORM Model
- Redis Client
- Environment 설정
- External API 공통 Client
- Logging 설정

위치: `infrastructure`

---

# ORM 규칙

ORM Model은 **Domain Entity와 반드시 분리해야 한다.**

ORM Model 위치: `domains/<domain>/infrastructure/orm`

## MUST 규칙

Domain Entity는 **SQLAlchemy Model을 import하면 안 된다.**

---

# Mapper 규칙

ORM Model과 Domain Entity 사이에는 **Mapper가 필요하다.**

위치: `domains/<domain>/infrastructure/mapper`

```
ORM Model → Domain Entity
Domain Entity → ORM Model
```

---

# Redis / DB / External API 규칙

- Redis Client는 **`infrastructure/cache`** 에 위치한다. Domain은 Redis를 알면 안 된다.
- DB Session은 **`infrastructure/database`** 에 위치한다. Domain은 DB를 알면 안 된다.
- External API Client는 **Outbound Adapter** 또는 **`infrastructure/external`** 에 위치한다. Domain은 External API를 알면 안 된다.

---

# Environment 설정 규칙

환경 변수는 **Pydantic BaseSettings 기반**으로 관리한다.

위치: `infrastructure/config/settings.py`

## MUST 규칙

Environment 변수는 **Domain Layer에서 사용하면 안 된다.**

---

# FastAPI Router 규칙

FastAPI Router는 **Inbound Adapter에 위치해야 한다.**

위치: `adapter/inbound/api` (공통) 또는 `domains/<domain>/adapter/inbound/api` (도메인별)

Router의 역할: Request DTO 수신 → UseCase 호출 → Response DTO 반환

## MUST 규칙

Router에서 **비즈니스 로직을 작성하면 안 된다.**

---

# Dependency Injection 규칙

의존성 흐름

```
Router → UseCase → Repository Port → Repository Adapter → Infrastructure
```

의존성 연결은 **FastAPI `Depends`** 로 수행한다. 도메인이 늘어 복잡해지면 별도 DI 컨테이너 도입을 검토할 수 있다.

---

# 새 도메인 만들기 — 단계별 가이드

`note` 도메인을 예시로, 4계층 + Repository + Mapper 패턴을 따라 새 도메인을 추가하는 단계.

## 1. 디렉토리 골격 생성

```
app/domains/note/
 ├ domain/
 │   ├ entity/note.py
 │   └ __init__.py
 ├ application/
 │   ├ port/note_repository_port.py
 │   ├ usecase/create_note.py
 │   ├ usecase/list_notes.py
 │   ├ request/create_note_request.py
 │   ├ response/note_response.py
 │   └ __init__.py
 ├ adapter/
 │   ├ inbound/api/note_router.py
 │   └ outbound/persistence/note_repository.py
 └ infrastructure/
     ├ orm/note_orm.py
     └ mapper/note_mapper.py
```

## 2. Domain Entity (순수 Python)

```python
# app/domains/note/domain/entity/note.py
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Note:
    id: int | None
    title: str
    content: str
    created_at: datetime
```

## 3. Repository Port (Application Layer ABC)

```python
# app/domains/note/application/port/note_repository_port.py
from abc import ABC, abstractmethod
from app.domains.note.domain.entity.note import Note

class NoteRepositoryPort(ABC):
    @abstractmethod
    async def save(self, note: Note) -> Note: ...

    @abstractmethod
    async def list_all(self) -> list[Note]: ...
```

## 4. UseCase (Domain + Port 조합)

```python
# app/domains/note/application/usecase/create_note.py
from datetime import datetime
from app.domains.note.application.port.note_repository_port import NoteRepositoryPort
from app.domains.note.domain.entity.note import Note

class CreateNoteUseCase:
    def __init__(self, repo: NoteRepositoryPort):
        self._repo = repo

    async def execute(self, title: str, content: str) -> Note:
        note = Note(id=None, title=title, content=content, created_at=datetime.utcnow())
        return await self._repo.save(note)
```

## 5. ORM Model (Infrastructure)

```python
# app/domains/note/infrastructure/orm/note_orm.py
from datetime import datetime
from sqlalchemy import String, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.infrastructure.database.database import Base

class NoteORM(Base):
    __tablename__ = "notes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
```

## 6. Mapper

```python
# app/domains/note/infrastructure/mapper/note_mapper.py
from app.domains.note.domain.entity.note import Note
from app.domains.note.infrastructure.orm.note_orm import NoteORM

def to_entity(orm: NoteORM) -> Note:
    return Note(id=orm.id, title=orm.title, content=orm.content, created_at=orm.created_at)

def to_orm(entity: Note) -> NoteORM:
    return NoteORM(title=entity.title, content=entity.content, created_at=entity.created_at)
```

## 7. Repository Adapter (Outbound)

```python
# app/domains/note/adapter/outbound/persistence/note_repository.py
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.domains.note.application.port.note_repository_port import NoteRepositoryPort
from app.domains.note.domain.entity.note import Note
from app.domains.note.infrastructure.mapper.note_mapper import to_entity, to_orm
from app.domains.note.infrastructure.orm.note_orm import NoteORM

class NoteRepository(NoteRepositoryPort):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def save(self, note: Note) -> Note:
        orm = to_orm(note)
        self._session.add(orm)
        await self._session.commit()
        await self._session.refresh(orm)
        return to_entity(orm)

    async def list_all(self) -> list[Note]:
        result = await self._session.execute(select(NoteORM))
        return [to_entity(o) for o in result.scalars().all()]
```

## 8. Router (Inbound)

```python
# app/domains/note/adapter/inbound/api/note_router.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.common.response.base_response import BaseResponse
from app.domains.note.adapter.outbound.persistence.note_repository import NoteRepository
from app.domains.note.application.usecase.create_note import CreateNoteUseCase
from app.infrastructure.database.database import get_db

router = APIRouter(prefix="/notes", tags=["notes"])

@router.post("", response_model=BaseResponse[dict])
async def create_note(
    title: str,
    content: str,
    session: AsyncSession = Depends(get_db),
):
    usecase = CreateNoteUseCase(NoteRepository(session))
    note = await usecase.execute(title=title, content=content)
    return BaseResponse.ok(data={"id": note.id, "title": note.title})
```

## 9. v1_router에 등록

```python
# app/adapter/inbound/api/v1_router.py
from app.domains.note.adapter.inbound.api.note_router import router as note_router
api_v1_router.include_router(note_router)
```

## 10. Alembic 마이그레이션

```bash
# alembic/env.py에 ORM import 추가
#   import app.domains.note.infrastructure.orm.note_orm  # noqa: F401
alembic revision --autogenerate -m "create note table"
alembic upgrade head
```

---

# 금지 사항

다음 코드는 **절대 작성하면 안 된다.**

### Domain에서 ORM 사용
```python
from sqlalchemy import Column   # ❌
```

### Domain에서 FastAPI 사용
```python
from fastapi import APIRouter   # ❌
```

### UseCase에서 Redis/DB 직접 생성
```python
redis.Redis(...)                # ❌
create_async_engine(...)        # ❌
```

---

# 최종 원칙

- Domain Layer는 순수 Python이어야 한다.
- ORM Model은 Domain Entity와 분리되어야 한다.
- Request / Response DTO는 Domain Entity와 분리되어야 한다.
- Redis / Database / External API는 Infrastructure 또는 Adapter에서만 사용해야 한다.
- Router에는 비즈니스 로직을 작성하면 안 된다.

모든 코드는 **이 CLAUDE.md 규칙을 MUST 준수해야 한다.**
