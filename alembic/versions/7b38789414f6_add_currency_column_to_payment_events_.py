"""add currency column to payment_events and transactions

Revision ID: 7b38789414f6
Revises: 7476a570439e
Create Date: 2026-05-06 10:23:39.393664

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '7b38789414f6'
down_revision: Union[str, Sequence[str], None] = '7476a570439e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1) currency 컬럼 추가. NOT NULL 인 채로 기존 row 가 깨지지 않도록 server_default="KRW".
    op.add_column(
        "payment_events",
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="KRW"),
    )
    op.add_column(
        "transactions",
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="KRW"),
    )

    # 2) 기존 raw_data['currency']='USD' 인 payment_events 의 currency 컬럼을 USD 로 백필.
    op.execute(
        "UPDATE payment_events SET currency='USD' WHERE raw_data->>'currency'='USD'"
    )
    # 3) raw_data 에 남아있던 currency 키는 제거 (정식 컬럼으로 승격됨).
    op.execute("UPDATE payment_events SET raw_data = raw_data - 'currency'")

    # 4) PaymentEvent 의 currency 를 따라 transactions 도 백필.
    op.execute(
        """
        UPDATE transactions t
        SET currency = pe.currency
        FROM payment_events pe
        WHERE pe.transaction_id = t.id
          AND pe.currency <> 'KRW'
        """
    )

    # 5) server_default 는 한번만 쓰고 제거. 이후 코드가 명시하도록.
    op.alter_column("payment_events", "currency", server_default=None)
    op.alter_column("transactions", "currency", server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    # raw_data 에 currency 키 복원 (USD 만)
    op.execute(
        "UPDATE payment_events SET raw_data = raw_data || jsonb_build_object('currency', currency) "
        "WHERE currency='USD'"
    )
    op.drop_column("transactions", "currency")
    op.drop_column("payment_events", "currency")
