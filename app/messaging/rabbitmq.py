
import json

import pika


RABBITMQ_HOST = "localhost"
RABBITMQ_PORT = 5672

QUEUE_NAME = "webhook_deliveries"
DLQ_NAME = "webhook_dead_letters"

RETRY_QUEUES = {
    2: "webhook_retry_2s",
    4: "webhook_retry_4s",
    8: "webhook_retry_8s",
    16: "webhook_retry_16s",
}

RETRY_DELAYS = {
    2: 2000,
    4: 4000,
    8: 8000,
    16: 16000,
}


def get_connection():
    credentials = pika.PlainCredentials(
        "guest",
        "guest"
    )

    parameters = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        port=RABBITMQ_PORT,
        credentials=credentials
    )

    return pika.BlockingConnection(parameters)


def create_queue(queue_name: str):
    connection = get_connection()
    channel = connection.channel()

    # Dead Letter Queue
    channel.queue_declare(
        queue=DLQ_NAME,
        durable=True
    )

    # Main delivery queue
    channel.queue_declare(
        queue=QUEUE_NAME,
        durable=True,
        arguments={
            "x-dead-letter-exchange": "",
            "x-dead-letter-routing-key": DLQ_NAME
        }
    )

    # Retry queues
    for delay, retry_queue in RETRY_QUEUES.items():
        channel.queue_declare(
            queue=retry_queue,
            durable=True,
            arguments={
                "x-message-ttl": RETRY_DELAYS[delay],
                "x-dead-letter-exchange": "",
                "x-dead-letter-routing-key": QUEUE_NAME
            }
        )

    connection.close()


def publish_delivery(delivery_id: int):
    connection = get_connection()
    channel = connection.channel()

    message = json.dumps({
        "delivery_id": delivery_id
    })

    channel.basic_publish(
        exchange="",
        routing_key=QUEUE_NAME,
        body=message,
        properties=pika.BasicProperties(
            delivery_mode=2
        )
    )

    connection.close()


def publish_retry(
    delivery_id: int,
    retry_delay: int
):
    if retry_delay not in RETRY_QUEUES:
        raise ValueError(
            f"Unsupported retry delay: {retry_delay}"
        )

    connection = get_connection()
    channel = connection.channel()

    retry_queue = RETRY_QUEUES[retry_delay]

    message = json.dumps({
        "delivery_id": delivery_id
    })

    channel.basic_publish(
        exchange="",
        routing_key=retry_queue,
        body=message,
        properties=pika.BasicProperties(
            delivery_mode=2
        )
    )

    print(
        f"Delivery {delivery_id} scheduled in "
        f"{retry_delay} seconds"
    )

    connection.close()


def publish_dead_letter(delivery_id: int):
    connection = get_connection()
    channel = connection.channel()

    message = json.dumps({
        "delivery_id": delivery_id
    })

    channel.basic_publish(
        exchange="",
        routing_key=DLQ_NAME,
        body=message,
        properties=pika.BasicProperties(
            delivery_mode=2
        )
    )

    connection.close()

