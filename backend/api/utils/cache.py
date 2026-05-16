import json
import os
from redis import asyncio as aioredis

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")

redis = aioredis.from_url(REDIS_URL, decode_responses=True)

CANDLE_TTL = 60


async def get_cached_candles(symbol: str, tf: str, offset: int) -> list | None:
    if offset == 0:
        return None
    key = f"candles:{symbol}:{tf}:{offset}"
    data = await redis.get(key)
    if data:
        await redis.expire(key, CANDLE_TTL)
        return json.loads(data)
    return None


async def cache_candles(symbol: str, tf: str, offset: int, candles: list, ttl: int = CANDLE_TTL):
    if not candles:
        return None
    
    key = f"candles:{symbol}:{tf}:{offset}"
    await redis.setex(key, ttl, json.dumps(candles, default=str))