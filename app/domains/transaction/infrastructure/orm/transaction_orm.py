"""transaction 도메인 ORM 모델 (PRD 2.1 transactions + processing_runs)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.database import Base


class TransactionORM(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        Index("ix_transactions_paid_at", "paid_at"),
        Index("ix_transactions_category", "category"),
        Index("ix_transactions_canonical_merchant", "canonical_merchant"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)

    merchant_name: Mapped[str] = mapped_column(String(255), nullable=False)
    canonical_merchant: Mapped[str | None] = mapped_column(String(255), nullable=True)
    amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    paid_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    payment_method: Mapped[str] = mapped_column(String(50), nullable=False, default="unknown")
    card_company: Mapped[str | None] = mapped_column(String(50), nullable=True)
    card_last4: Mapped[str | None] = mapped_column(String(4), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    requires_manual_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class ProcessingRunORM(Base):
    __tablename__ = "processing_runs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    emails_fetched: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    events_parsed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    transactions_created: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    errors: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
