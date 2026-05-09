from __future__ import annotations

from app.domains.payment_event.domain.entity.payment_event import PaymentEvent
from app.domains.payment_event.domain.value_object.event_type import EventType
from app.domains.payment_event.infrastructure.orm.payment_event_orm import PaymentEventORM


def to_entity(orm: PaymentEventORM) -> PaymentEvent:
    return PaymentEvent(
        id=orm.id,
        user_id=orm.user_id,
        email_id=orm.email_id,
        transaction_id=orm.transaction_id,
        event_type=EventType(orm.event_type),
        merchant_name=orm.merchant_name,
        amount=orm.amount,
        currency=orm.currency,
        paid_at=orm.paid_at,
        card_company=orm.card_company,
        card_last4=orm.card_last4,
        raw_data=dict(orm.raw_data) if orm.raw_data else {},
        parser_name=orm.parser_name,
        confidence=orm.confidence,
        requires_manual_review=orm.requires_manual_review,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


def to_orm(entity: PaymentEvent) -> PaymentEventORM:
    return PaymentEventORM(
        user_id=entity.user_id,
        email_id=entity.email_id,
        transaction_id=entity.transaction_id,
        event_type=str(entity.event_type),
        merchant_name=entity.merchant_name,
        amount=entity.amount,
        currency=entity.currency,
        paid_at=entity.paid_at,
        card_company=entity.card_company,
        card_last4=entity.card_last4,
        raw_data=entity.raw_data,
        parser_name=entity.parser_name,
        confidence=entity.confidence,
        requires_manual_review=entity.requires_manual_review,
    )
