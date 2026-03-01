from slowapi import Limiter
from slowapi.util import get_remote_address
from redis.asyncio import Redis
from app.config import settings

redis_client = Redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.redis_url,
    default_limits=[f"{settings.rate_limit_per_minute}/minute"]
)
