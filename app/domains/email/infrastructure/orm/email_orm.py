"""email 도메인 ORM 모델.

PRD 2.1 emails 테이블 + OAuth 토큰 저장 테이블.
도메인 Entity는 별도 파일에서 관리하고 Mapper로 변환한다 (CLAUDE.md ORM 규칙).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Index,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.database import Base


class EmailORM(Base):
    __tablename__ = "emails"
    __table_args__ = (
        UniqueConstraint("source", "account", "message_id", name="uq_emails_source_account_msg"),
        Index("ix_emails_parsed_status", "parsed_status"),
        Index("ix_emails_received_at", "received_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    account: Mapped[str] = mapped_column(String(255), nullable=False)
    message_id: Mapped[str] = mapped_column(String(500), nullable=False)
    sender: Mapped[str] = mapped_column(String(500), nullable=False)
    subject: Mapped[str] = mapped_column(Text, nullable=False, default="")
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    body_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    body_html: Mapped[str] = mapped_column(Text, nullable=False, default="")
    labels: Mapped[str] = mapped_column(String(1000), nullable=False, default="")
    parsed_status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    parse_failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class OAuthTokenORM(Base):
    __tablename__ = "oauth_tokens"
    __table_args__ = (UniqueConstraint("source", "account", name="uq_oauth_tokens_source_account"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    account: Mapped[str] = mapped_column(String(255), nullable=False)
    encrypted_access_token: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    encrypted_refresh_token: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scopes: Mapped[str] = mapped_column(String(1000), nullable=False, default="")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
