from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # 환경
    env: str = "local"
    debug: bool = False

    # PostgreSQL
    postgres_user: str
    postgres_password: str
    postgres_host: str
    postgres_port: int = 5432
    postgres_db: str

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: Optional[str] = None

    # 인증 (JWT)
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    session_ttl_seconds: int = 86400

    # CORS
    cors_allowed_frontend_url: str = "http://localhost:3000"

    # Logging
    log_level: str = "INFO"

    # 애플리케이션 시간대 (PRD 4.2/8.1)
    timezone: str = "Asia/Seoul"

    # Phase 1 단일 사용자 가정 (Phase 2에서 사용자 도메인 도입 시 제거)
    owner_user_id: int = 1

    # Anthropic / LLM
    anthropic_api_key: str = ""
    llm_parser_model: str = "claude-haiku-4-5-20251001"
    llm_disambiguator_model: str = "claude-haiku-4-5-20251001"
    llm_cache_ttl_seconds: int = 86400

    # Gmail OAuth (PRD 8.1)
    gmail_oauth_client_id: str = ""
    gmail_oauth_client_secret: str = ""
    gmail_oauth_redirect_uri: str = "http://localhost:8000/api/v1/auth/gmail/callback"

    # OAuth 토큰 암호화 (Fernet 키, 운영은 KMS/Secrets Manager 권장)
    # `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
    token_encryption_key: str = ""

    # Sync 파이프라인 동시 실행 차단용 Redis lock TTL
    sync_lock_ttl_seconds: int = 600

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
