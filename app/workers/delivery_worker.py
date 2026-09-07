
import hashlib
import hmac
import json
import time

import httpx
import pika
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.messaging.rabbitmq import (
    publish_dead_letter,
    publish_retry
)
from app.models.delivery import Delivery
from app.models.event import Event
from app.models.webhook import Webhook
from app.services.rate_limiter import is_rate_limited


QUEUE_NAME = "webhook_deliveries"
DLQ_NAME = "webhook_dead_letters"

MAX_ATTEMPTS = 5


def get_rabbitmq_connection():
    credentials = pika.PlainCredentials(
        "guest",
        "guest"
    )

    parameters = pika.ConnectionParameters(
        host="localhost",
        port=5672,
        credentials=credentials
    )

    return pika.BlockingConnection(parameters)


def process_delivery(delivery_id: int):
    db: Session = SessionLocal()

    try:
        # Get delivery
        delivery = db.query(Delivery).filter(
            Delivery.id == delivery_id
        ).first()

        if not delivery:
            print(
                f"Delivery {delivery_id} not found"
            )
            return

        # Get webhook
        webhook = db.query(Webhook).filter(
            Webhook.id == delivery.webhook_id
        ).first()

        # Get event
        event = db.query(Event).filter(
            Event.id == delivery.event_id
        ).first()

        if not webhook or not event:
            print(
                f"Missing webhook/event for delivery "
                f"{delivery_id}"
            )
            return

        # Build webhook payload
        payload = {
            "event_id": event.id,
            "event_type": event.event_type,
            "data": event.payload
        }

        # Convert payload to deterministic JSON
        payload_json = json.dumps(
            payload,
            separators=(",", ":"),
            sort_keys=True
        )

        # Generate HMAC-SHA256 signature
        signature = hmac.new(
            webhook.secret.encode(),
            payload_json.encode(),
            hashlib.sha256
        ).hexdigest()

        # Check Redis rate limit BEFORE consuming
        # a delivery attempt.
        if is_rate_limited(webhook.id):
            print(
                f"Rate limit reached for webhook "
                f"{webhook.id}. Waiting 5 seconds..."
            )

            time.sleep(5)

            process_delivery(delivery_id)

            return

        # Increase attempt count only when
        # an actual delivery attempt is made.
        delivery.attempts += 1
        current_attempt = delivery.attempts

        db.commit()

        print(
            f"Attempt {current_attempt}/{MAX_ATTEMPTS} "
            f"for delivery {delivery_id}"
        )

        # Send webhook
        response = httpx.post(
            webhook.url,
            json=payload,
            headers={
                "X-Webhook-Signature": signature
            },
            timeout=10
        )

        delivery.response_status = response.status_code

        # Successful delivery
        if 200 <= response.status_code < 300:
            delivery.status = "success"

            db.commit()

            print(
                f"Delivery {delivery_id} succeeded "
                f"with status {response.status_code}"
            )

            return

        # Webhook returned an error
        print(
            f"Delivery {delivery_id} returned "
            f"status {response.status_code}"
        )

        # Maximum attempts reached
        if current_attempt >= MAX_ATTEMPTS:
            delivery.status = "failed"

            db.commit()

            publish_dead_letter(delivery_id)

            print(
                f"Delivery {delivery_id} permanently failed "
                f"after {MAX_ATTEMPTS} attempts"
            )

            print(
                f"Delivery {delivery_id} moved to "
                f"dead letter queue"
            )

            return

        # Schedule retry through RabbitMQ.
        #
        # Currently the retry queue has a 2-second TTL.
        
        
        retry_delay=2** current_attempt
        print(
            f"Scheduling retry for delivery "
            f"{delivery_id} in {retry_delay} seconds..."
        )

        db.commit()

        publish_retry(
            delivery_id,
            retry_delay
        )

    except Exception as error:
        print(
            f"Delivery {delivery_id} error: {error}"
        )

        delivery = db.query(Delivery).filter(
            Delivery.id == delivery_id
        ).first()

        if delivery:
            delivery.attempts += 1

            if delivery.attempts >= MAX_ATTEMPTS:
                delivery.status = "failed"

                db.commit()

                publish_dead_letter(delivery_id)

                print(
                    f"Delivery {delivery_id} moved to "
                    f"dead letter queue"
                )

            else:
                db.commit()

    finally:
        db.close()


def callback(channel, method, properties, body):
    message = json.loads(body)

    delivery_id = message["delivery_id"]

    print(
        f"Received delivery job: {delivery_id}"
    )

    process_delivery(delivery_id)

    channel.basic_ack(
        delivery_tag=method.delivery_tag
    )


def start_worker():
    connection = get_rabbitmq_connection()

    channel = connection.channel()

    # Main queue configuration
    channel.queue_declare(
        queue=QUEUE_NAME,
        durable=True,
        arguments={
            "x-dead-letter-exchange": "",
            "x-dead-letter-routing-key": DLQ_NAME
        }
    )

    channel.basic_qos(
        prefetch_count=1
    )

    channel.basic_consume(
        queue=QUEUE_NAME,
        on_message_callback=callback
    )

    print("Delivery worker started...")
    print("Waiting for webhook deliveries...")

    channel.start_consuming()


if __name__ == "__main__":
    start_worker()

