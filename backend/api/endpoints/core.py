from fastapi import APIRouter, Request, Query
from fastapi.responses import JSONResponse
import httpx
from utils.cache import get_cached_candles, cache_candles

router = APIRouter()
CORE_SERVICE_URL = "http://core:18080"


@router.get("/coin/{symbol}")
async def get_coin(
    symbol: str,
    request: Request,
    tf: str = Query("1m"),
    offset: int = Query(0),
):

    if offset == 0:
        async with httpx.AsyncClient() as client:
            res = await client.get(
                f"{CORE_SERVICE_URL}/coin/{symbol}",
                params={"tf": tf, "offset": offset},
                timeout=10.0,
            )
            data = res.json()
            candles = data.get("data", [])
            
            if len(candles) > 1:
                last_candle = candles[-1]
                history_candles = candles[:-1]
                
                if history_candles:
                    await cache_candles(symbol, tf, 0, history_candles, ttl=60)
                
                return {
                    "symbol": symbol,
                    "time_frame": tf,
                    "data": candles,
                    "source": "mixed",
                    "cached_history": True
                }
            
            return data
    
    cached = await get_cached_candles(symbol, tf, offset)
    if cached is not None:
        return {
            "symbol": symbol,
            "time_frame": tf,
            "data": cached,
            "source": "cache",
        }
    
    async with httpx.AsyncClient() as client:
        res = await client.get(
            f"{CORE_SERVICE_URL}/coin/{symbol}",
            params={"tf": tf, "offset": offset},
            timeout=10.0,
        )
        data = res.json()
        candles = data.get("data", [])
        
        if candles:
            await cache_candles(symbol, tf, offset, candles)
        
        return data