from fastapi import FastAPI

from app.database import Base, engine

from app.models.webhook import Webhook, WebhookSubscription
from app.models.event import Event
from app.models.delivery import Delivery
from app.routers.event import router as event_router

from app.routers.webhook import router as webhook_router
from app.messaging.rabbitmq import create_queue

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Webhook Delivery Platform")

create_queue("webhook_deliveries")
create_queue("webhook_dead_letters")

app.include_router(webhook_router)
app.include_router(event_router)

@app.get("/")
def root():
    return {
        "message": "Webhook Delivery Platform is running"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }