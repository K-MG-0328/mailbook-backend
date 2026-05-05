from __future__ import annotations

from app.domains.transaction.domain.entity.transaction import Transaction
from app.domains.transaction.domain.value_object.payment_method import PaymentMethod
from app.domains.transaction.infrastructure.orm.transaction_orm import TransactionORM


def to_entity(orm: TransactionORM) -> Transaction:
    return Transaction(
        id=orm.id,
        user_id=orm.user_id,
        merchant_name=orm.merchant_name,
        canonical_merchant=orm.canonical_merchant,
        amount=orm.amount,
        paid_at=orm.paid_at,
        category=orm.category,
        payment_method=PaymentMethod(orm.payment_method),
        card_company=orm.card_company,
        card_last4=orm.card_last4,
        note=orm.note,
        is_verified=orm.is_verified,
        requires_manual_review=orm.requires_manual_review,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


def to_orm(entity: Transaction) -> TransactionORM:
    return TransactionORM(
        user_id=entity.user_id,
        merchant_name=entity.merchant_name,
        canonical_merchant=entity.canonical_merchant,
        amount=entity.amount,
        paid_at=entity.paid_at,
        category=entity.category,
        payment_method=str(entity.payment_method),
        card_company=entity.card_company,
        card_last4=entity.card_last4,
        note=entity.note,
        is_verified=entity.is_verified,
        requires_manual_review=entity.requires_manual_review,
    )
