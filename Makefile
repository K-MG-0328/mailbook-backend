.PHONY: help dev test lint fmt typecheck migrate migration up down logs clean install

help:
	@echo "Available targets:"
	@echo "  install     - uv sync (의존성 설치)"
	@echo "  dev         - uvicorn 개발 서버 (--reload)"
	@echo "  test        - pytest 실행"
	@echo "  lint        - ruff check + format check"
	@echo "  fmt         - ruff format (자동 포맷)"
	@echo "  typecheck   - mypy app"
	@echo "  migrate     - alembic upgrade head"
	@echo "  migration   - alembic revision --autogenerate -m '<msg>' (MSG=...)"
	@echo "  up          - docker compose up -d (postgres, redis)"
	@echo "  down        - docker compose down"
	@echo "  logs        - docker compose logs -f"
	@echo "  clean       - 캐시/빌드 산출물 정리"

install:
	uv sync

dev:
	uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000

test:
	uv run pytest -v

lint:
	uv run ruff check .
	uv run ruff format --check .

fmt:
	uv run ruff format .
	uv run ruff check --fix .

typecheck:
	uv run mypy app

migrate:
	uv run alembic upgrade head

migration:
	@if [ -z "$(MSG)" ]; then echo "Usage: make migration MSG='your message'"; exit 1; fi
	uv run alembic revision --autogenerate -m "$(MSG)"

up:
	docker compose up -d postgres redis

down:
	docker compose down

logs:
	docker compose logs -f

clean:
	rm -rf .pytest_cache .ruff_cache .mypy_cache __pycache__ build dist *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
