from typing import Any
from redis.asyncio import Redis
import json

class RedisCache:
    def __init__(self, client: Redis, default_ttl: int = 300):
        self._client = client
        self._default_ttl = default_ttl

    async def get(self, key: str) -> Any | None:
        raw = await self._client.get(key)
        return json.loads(raw) if raw is not None else None

    async def set(self, key: str, value: Any, ttl: int | None) -> None:
        if ttl is None:
            ttl = self._default_ttl
        await self._client.set(key, json.dumps(value), ex=ttl)

    async def delete(self, key: str) -> None:
        await self._client.delete(key)

    async def exists(self, key: str) -> bool:
        return bool(await self._client.exists(key))

