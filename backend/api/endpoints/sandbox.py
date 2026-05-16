from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
import httpx

router = APIRouter()

SANDBOX_SERVICE_URL = "http://sandbox:8010"


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_to_sandbox(path: str, request: Request):
    content = await request.body()

    async with httpx.AsyncClient() as client:
        try:
            response = await client.request(
                method=request.method,
                url=f"{SANDBOX_SERVICE_URL}/{path}",
                params=request.query_params,
                content=content,
                headers=dict(request.headers),
                timeout=120.0,
            )
        except httpx.RequestError as exc:
            return JSONResponse(
                status_code=502,
                content={"error": f"Sandbox service unreachable or timeout: {exc}"}
            )

        try:
            data = response.json()
        except Exception:
            data = {"detail": response.text}

        return JSONResponse(
            status_code=response.status_code,
            content=data,
        )