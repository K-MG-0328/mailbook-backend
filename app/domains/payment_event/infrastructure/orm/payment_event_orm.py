"""payment_event 도메인 ORM 모델 (PRD 2.1 payment_events).

FK는 다른 도메인 ORM 클래스를 import 하지 않고 테이블명 문자열로만 참조한다
(도메인 격리). transaction_id는 매칭 후에 채워지므로 nullable.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.database import Base


class PaymentEventORM(Base):
    __tablename__ = "payment_events"
    __table_args__ = (
        # PRD 2.1: 매칭 쿼리 최적화
        Index("ix_payment_events_amount_paid_at", "amount", "paid_at"),
        Index("ix_payment_events_transaction_id", "transaction_id"),
        Index("ix_payment_events_event_type", "event_type"),
        # 같은 이메일이 두 번 파싱돼 PaymentEvent 가 중복 생성되지 않도록 DB 레벨 보호.
        UniqueConstraint("email_id", name="uq_payment_events_email_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    email_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("emails.id", ondelete="CASCADE"),
        nullable=False,
    )
    transaction_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("transactions.id", ondelete="SET NULL"),
        nullable=True,
    )

    event_type: Mapped[str] = mapped_column(String(30), nullable=False)
    merchant_name: Mapped[str] = mapped_column(String(255), nullable=False)
    # KRW 는 원 단위, USD 는 cents 단위 정수.
    amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    # ISO 4217. amount 단위가 통화에 따라 다르므로 명시.
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    paid_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    card_company: Mapped[str | None] = mapped_column(String(50), nullable=True)
    card_last4: Mapped[str | None] = mapped_column(String(4), nullable=True)

    # JSONB on Postgres, fallback JSON on others (테스트용 SQLite 등)
    raw_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )
    parser_name: Mapped[str] = mapped_column(String(100), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
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
