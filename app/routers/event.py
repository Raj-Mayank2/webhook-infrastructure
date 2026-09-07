from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.event import Event
from app.models.delivery import Delivery
from app.models.webhook import WebhookSubscription
from app.schemas.event import EventCreate, EventResponse
from app.messaging.rabbitmq import publish_delivery


router = APIRouter(
    prefix="/events",
    tags=["Events"]
)


@router.post(
    "",
    response_model=EventResponse,
    status_code=status.HTTP_201_CREATED
)
def create_event(
    event: EventCreate,
    db: Session = Depends(get_db)
):
    # 1. Save the event
    new_event = Event(
        event_type=event.event_type,
        payload=event.payload
    )

    db.add(new_event)
    db.commit()
    db.refresh(new_event)

    # 2. Find webhooks subscribed to this event
    subscriptions = db.query(
        WebhookSubscription
    ).filter(
        WebhookSubscription.event_type == event.event_type
    ).all()

    # 3. Create a delivery for each subscription
    for subscription in subscriptions:

        delivery = Delivery(
            event_id=new_event.id,
            webhook_id=subscription.webhook_id,
            status="pending",
            attempts=0
        )

        db.add(delivery)
        db.commit()
        db.refresh(delivery)

        # 4. Send delivery job to RabbitMQ
        publish_delivery(delivery.id)

    return new_event