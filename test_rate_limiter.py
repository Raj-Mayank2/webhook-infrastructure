from app.services.rate_limiter import is_rate_limited


webhook_id = 1

for i in range(105):
    limited = is_rate_limited(webhook_id)

    print(
        f"Request {i + 1}: "
        f"{'BLOCKED' if limited else 'ALLOWED'}"
    )