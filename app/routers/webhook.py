from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import secrets
from app.database import get_db
from app.models.webhook import Webhook, WebhookSubscription
from app.schemas.webhook import WebhookCreate, WebhookResponse
from app.schemas.subscription import (
    SubscriptionCreate,
    SubscriptionResponse
)
router = APIRouter(
    prefix="/webhooks",
    tags=["Webhooks"]
)


@router.post(
    "",
    response_model=WebhookResponse,
    status_code=status.HTTP_201_CREATED
)
def create_webhook(
    webhook: WebhookCreate,
    db: Session = Depends(get_db)
):
    new_webhook = Webhook(
    url=str(webhook.url),
    secret=secrets.token_hex(32)
)

    db.add(new_webhook)
    db.commit()
    db.refresh(new_webhook)

    return new_webhook


@router.get(
    "",
    response_model=list[WebhookResponse]
)
def get_webhooks(
    db: Session = Depends(get_db)
):
    webhooks = db.query(Webhook).all()

    return webhooks


@router.delete(
    "/{webhook_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
def delete_webhook(
    webhook_id: int,
    db: Session = Depends(get_db)
):
    webhook = db.query(Webhook).filter(
        Webhook.id == webhook_id
    ).first()

    if not webhook:
        raise HTTPException(
            status_code=404,
            detail="Webhook not found"
        )

    db.delete(webhook)
    db.commit()



@router.post(
    "/{webhook_id}/subscriptions",
    response_model=SubscriptionResponse,
    status_code=status.HTTP_201_CREATED
)
def create_subscription(
    webhook_id: int,
    subscription: SubscriptionCreate,
    db: Session = Depends(get_db)
):
    webhook = db.query(Webhook).filter(
        Webhook.id == webhook_id
    ).first()

    if not webhook:
        raise HTTPException(
            status_code=404,
            detail="Webhook not found"
        )

    new_subscription = WebhookSubscription(
        webhook_id=webhook_id,
        event_type=subscription.event_type
    )

    db.add(new_subscription)
    db.commit()
    db.refresh(new_subscription)

    return new_subscription