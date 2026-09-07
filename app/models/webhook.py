from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base


class Webhook(Base):
    __tablename__ = "webhooks"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, nullable=False)

    secret=Column(
        String,
        nullable=False
    )

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    subscriptions = relationship(
        "WebhookSubscription",
        back_populates="webhook",
        cascade="all, delete-orphan"
    )


class WebhookSubscription(Base):
    __tablename__ = "webhook_subscriptions"

    id = Column(Integer, primary_key=True, index=True)

    webhook_id = Column(
        Integer,
        ForeignKey("webhooks.id"),
        nullable=False
    )

    event_type = Column(String, nullable=False)

    webhook = relationship(
        "Webhook",
        back_populates="subscriptions"
    )