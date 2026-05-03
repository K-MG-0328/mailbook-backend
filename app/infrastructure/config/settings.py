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

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
