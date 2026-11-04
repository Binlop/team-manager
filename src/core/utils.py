from functools import wraps
from redis_fastapi.cache_backend import CacheBackend


def cached(redis_key: str, redis_cache: CacheBackend, ttl: int):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwagrs):
            cached = redis_cache.get(redis_key)
            if cached is not None:
                return cached
            res = func(*args, **kwagrs)
            return res
        return func
    