"""merchant 도메인 ORM 모델 (PRD 2.1 merchant_aliases)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Float,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.database import Base


class MerchantAliasORM(Base):
    __tablename__ = "merchant_aliases"
    __table_args__ = (
        # 같은 사용자 내에서 raw_name은 유일. user_id 가 NULL인 시드 데이터(yaml)도
        # postgres NULLS NOT DISTINCT 기본 동작으로 단일 글로벌 행을 보장하지 않으므로,
        # learned_from='yaml' 시드는 재실행 시 upsert로 처리한다 (seed usecase에서).
        UniqueConstraint("user_id", "raw_name", name="uq_merchant_aliases_user_raw"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)

    raw_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    canonical: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    learned_from: Mapped[str] = mapped_column(String(20), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
