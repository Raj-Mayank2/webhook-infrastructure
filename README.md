# Reliable Webhook Delivery Platform

A backend infrastructure project for reliable, asynchronous webhook
delivery.

The platform accepts events, finds subscribed webhooks, creates delivery
jobs, and processes them asynchronously using RabbitMQ workers. It
includes retry handling, exponential backoff, dead-letter queues,
HMAC-SHA256 webhook signing, and Redis-based rate limiting.

## Features

-   REST API built with FastAPI
-   PostgreSQL persistence using SQLAlchemy
-   Asynchronous event processing with RabbitMQ
-   Dedicated delivery worker
-   Automatic webhook retries
-   Exponential backoff: 2s, 4s, 8s, 16s
-   Dead Letter Queue (DLQ) after maximum delivery attempts
-   HMAC-SHA256 webhook signatures
-   Redis-based per-webhook rate limiting
-   Durable RabbitMQ queues and messages
-   Docker-based infrastructure
-   Swagger/OpenAPI API documentation

## Architecture

``` text
                         Client
                           |
                           v
                    +-------------+
                    |   FastAPI   |
                    |     API     |
                    +------+------+
                           |
             +-------------+-------------+
             |             |             |
             v             v             v
        PostgreSQL      RabbitMQ       Redis
             |             |          Rate Limit
             |             v
             |      webhook_deliveries
             |             |
             |             v
             |      +-------------+
             +----> |   Worker    |
                    +------+------+
                           |
                    HMAC Signature
                           |
                           v
                   Customer Webhook
                           |
                    +------+------+
                    |             |
                  2xx          4xx/5xx
                    |             |
                 Success       Retry Queue
                                  |
                           2s → 4s → 8s → 16s
                                  |
                             Max Attempts
                                  |
                                  v
                                 DLQ
```

## Tech Stack

  Technology   Purpose
  ------------ -------------------------------------------
  Python       Backend development
  FastAPI      REST API
  PostgreSQL   Persistent data storage
  SQLAlchemy   Database ORM
  RabbitMQ     Message broker and asynchronous delivery
  Redis        Rate limiting
  HTTPX        Outgoing HTTP requests
  Pika         RabbitMQ client
  Docker       Infrastructure and application containers

## Project Structure

``` text
webhook-infrastructure/
├── app/
│   ├── models/
│   │   ├── webhook.py
│   │   ├── event.py
│   │   └── delivery.py
│   ├── schemas/
│   │   ├── webhook.py
│   │   ├── subscription.py
│   │   └── event.py
│   ├── routers/
│   │   ├── webhook.py
│   │   └── event.py
│   ├── messaging/
│   │   └── rabbitmq.py
│   ├── services/
│   │   └── rate_limiter.py
│   ├── workers/
│   │   └── delivery_worker.py
│   ├── database.py
│   ├── redis_client.py
│   └── main.py
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

## API

### Create Webhook

``` http
POST /webhooks
```

Request:

``` json
{
  "url": "https://example.com/webhook"
}
```

A unique secret is generated automatically for the webhook.

### List Webhooks

``` http
GET /webhooks
```

### Delete Webhook

``` http
DELETE /webhooks/{webhook_id}
```

### Subscribe to an Event

``` http
POST /webhooks/{webhook_id}/subscriptions
```

Request:

``` json
{
  "event_type": "order.created"
}
```

### Create Event

``` http
POST /events
```

Request:

``` json
{
  "event_type": "order.created",
  "payload": {
    "order_id": 123,
    "amount": 999
  }
}
```

The API creates delivery records for matching subscriptions and
publishes delivery jobs to RabbitMQ.

## Reliable Delivery

Each delivery tracks:

-   Delivery status
-   Number of attempts
-   HTTP response status
-   Event ID
-   Webhook ID
-   Creation timestamp

A successful `2xx` response marks the delivery as successful.

A failed HTTP response triggers a retry.

### Retry Strategy

``` text
Attempt 1 → 2 seconds
Attempt 2 → 4 seconds
Attempt 3 → 8 seconds
Attempt 4 → 16 seconds
Attempt 5 → Failed + DLQ
```

RabbitMQ TTL queues are used to delay retries without keeping the worker
blocked during the retry interval.

## Dead Letter Queue

After the maximum number of attempts is reached, the delivery is marked
as permanently failed and moved to:

``` text
webhook_dead_letters
```

This allows failed deliveries to be isolated for later inspection or
recovery.

## HMAC Webhook Security

Every webhook receives a server-generated secret.

Before sending a webhook, the worker calculates an HMAC-SHA256 signature
from the deterministic JSON payload.

The signature is sent using:

``` http
X-Webhook-Signature: <signature>
```

A receiving application can independently calculate the signature using
its stored secret and compare the values before accepting the request.

## Redis Rate Limiting

Redis tracks delivery requests per webhook using a key such as:

``` text
rate_limit:webhook:{webhook_id}
```

The current configuration allows:

``` text
100 requests / 60 seconds / webhook
```

This prevents a single webhook destination from overwhelming the
delivery system.

## Running Locally

### Prerequisites

-   Python 3.13+
-   Docker Desktop
-   Docker Compose

PostgreSQL, Redis, and RabbitMQ run through Docker, so they do not need
to be installed directly on the host machine.

### Start Infrastructure

``` powershell
docker compose up -d
```

Check containers:

``` powershell
docker compose ps
```

### Create Virtual Environment

``` powershell
python -m venv venv
```

Activate it on Windows PowerShell:

``` powershell
.\venv\Scripts\Activate.ps1
```

Install dependencies:

``` powershell
pip install -r requirements.txt
```

### Start API

``` powershell
uvicorn app.main:app --reload
```

The API runs on:

``` text
http://127.0.0.1:8000
```

Swagger documentation is available at:

``` text
http://127.0.0.1:8000/docs
```

### Start Worker

In a second terminal:

``` powershell
.\venv\Scripts\Activate.ps1
python -m app.workers.delivery_worker
```

The worker consumes jobs from RabbitMQ and delivers them to customer
webhooks.

## RabbitMQ Management

RabbitMQ's management interface is available locally on port `15672`.

Default development credentials:

``` text
Username: guest
Password: guest
```

## Testing the Delivery Flow

A simple successful test can use:

``` text
https://httpbin.org/anything
```

A failure/retry test can use:

``` text
https://httpbin.org/status/500
```

For the failing endpoint, the worker should demonstrate the retry
sequence and eventually move the delivery to the dead-letter queue.

## Database Model

The main entities are:

``` text
Webhook
   |
   +--- WebhookSubscription
             |
             | event_type
             |
Event -------+
   |
   +--- Delivery
             |
             +--- Webhook
```

`Delivery` acts as the record connecting an event to a specific webhook
destination.

## Current Development Status

Implemented:

-   FastAPI API
-   PostgreSQL persistence
-   RabbitMQ asynchronous delivery
-   Delivery worker
-   Retry handling
-   Exponential backoff
-   Dead Letter Queue
-   HMAC-SHA256 signing
-   Redis rate limiting
-   Docker infrastructure

Planned improvements:

-   Idempotency and duplicate protection
-   Production-grade retry scheduling
-   Improved rate-limit scheduling
-   Automated tests
-   Structured logging and monitoring
-   Alembic database migrations
-   Full application containerization
-   Production deployment
-   Architecture documentation and observability

## Why This Project?

Webhooks are commonly used for event-driven communication between
services, but simply making an HTTP request is not enough for reliable
delivery.

This project explores backend infrastructure concerns such as:

-   Asynchronous processing
-   Message queues
-   Failure handling
-   Retry strategies
-   Dead-letter processing
-   Request authentication
-   Rate limiting
-   Persistent delivery state
-   Worker-based architecture
-   Containerized infrastructure

The goal is to demonstrate practical distributed-systems and backend
engineering concepts rather than only CRUD API development.

## License

This project is intended for educational and portfolio use.
