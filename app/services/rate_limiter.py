import time

from app.redis_client import redis_client


RATE_LIMIT = 100
WINDOW_SECONDS = 60


def is_rate_limited(webhook_id: int) -> bool:
    key = f"rate_limit:webhook:{webhook_id}"

    current_count = redis_client.incr(key)

    if current_count == 1:
        redis_client.expire(
            key,
            WINDOW_SECONDS
        )

    return current_count > RATE_LIMIT