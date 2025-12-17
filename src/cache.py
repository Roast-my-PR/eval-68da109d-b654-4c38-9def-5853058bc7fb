import json
import redis
from typing import Optional, Any
from datetime import timedelta

from config import get_settings

settings = get_settings()

redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)


class CacheService:
    def __init__(self):
        self.client = redis_client
        self.default_ttl = 3600

    def get(self, key: str) -> Optional[Any]:
        value = self.client.get(key)
        if value:
            return json.loads(value)
        return None

    def set(self, key: str, value: Any, ttl: int = None) -> bool:
        ttl = ttl or self.default_ttl
        serialized = json.dumps(value)
        return self.client.set(key, serialized, ex=ttl)

    def delete(self, key: str) -> bool:
        return self.client.delete(key) > 0

    def get_campaign_metrics(self, campaign_id: int, date: str) -> Optional[dict]:
        key = f"metrics:{campaign_id}:{date}"
        return self.get(key)

    def set_campaign_metrics(self, campaign_id: int, date: str, metrics: dict) -> bool:
        key = f"metrics:{campaign_id}:{date}"
        return self.set(key, metrics, ttl=1800)

    def invalidate_campaign_cache(self, campaign_id: int):
        pattern = f"metrics:{campaign_id}:*"
        keys = self.client.keys(pattern)
        if keys:
            self.client.delete(*keys)

    def acquire_lock(self, lock_name: str, timeout: int = 10) -> bool:
        lock_key = f"lock:{lock_name}"
        acquired = self.client.set(lock_key, "1", nx=True, ex=timeout)
        return acquired is not None

    def release_lock(self, lock_name: str) -> bool:
        lock_key = f"lock:{lock_name}"
        return self.client.delete(lock_key) > 0

    def increment_counter(self, key: str, amount: int = 1) -> int:
        return self.client.incrby(key, amount)

    def get_rate_limit_count(self, user_id: int, endpoint: str) -> int:
        key = f"ratelimit:{user_id}:{endpoint}"
        count = self.client.get(key)
        return int(count) if count else 0

    def increment_rate_limit(self, user_id: int, endpoint: str, window: int = 60) -> int:
        key = f"ratelimit:{user_id}:{endpoint}"
        pipe = self.client.pipeline()
        pipe.incr(key)
        pipe.expire(key, window)
        results = pipe.execute()
        return results[0]


cache_service = CacheService()
