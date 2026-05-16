import os
import httpx
from redis import asyncio as aioredis

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")
USERS_URL = os.getenv("USERS_URL", "http://users:8005")

redis = aioredis.from_url(REDIS_URL, decode_responses=True)


async def get_user_id_from_token(token: str) -> int | None:
    """Достаём user_id из JWT, кэшируем в Redis на 5 минут."""
    if not token:
        return None

    cache_key = f"session:{token}"
    cached = await redis.get(cache_key)
    if cached:
        await redis.expire(cache_key, 300)
        return int(cached)

    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(
                f"{USERS_URL}/me",
                headers={"Authorization": f"Bearer {token}"},
                timeout=5.0,
            )
            if res.status_code == 200:
                user_id = res.json()["id"]
                await redis.setex(cache_key, 300, user_id)
                return user_id
    except Exception:
        pass

    return None