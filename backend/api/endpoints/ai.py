from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
import httpx
from utils.auth import get_user_id_from_token

router = APIRouter()
AI_SERVICE_URL = "http://ai:9000"


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_to_ai(path: str, request: Request):
    content = await request.body()
    headers = dict(request.headers)
    
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "")
    
    # ОТЛАДКА
    print(f"=== AI PROXY DEBUG ===")
    print(f"Path: {path}")
    print(f"Authorization header: {auth_header[:50] if auth_header else 'MISSING'}...")
    print(f"Token: {token[:20] if token else 'MISSING'}...")
    
    user_id = None
    if token:
        user_id = await get_user_id_from_token(token)
        print(f"Resolved user_id: {user_id}")
        if user_id:
            headers["X-User-ID"] = str(user_id)
    else:
        print("No token found in request!")
    
    print(f"Forwarding to AI with X-User-ID: {headers.get('X-User-ID', 'MISSING')}")
    print("=======================")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.request(
                method=request.method,
                url=f"{AI_SERVICE_URL}/{path}",
                params=request.query_params,
                content=content,
                headers=headers,
                timeout=120.0,
            )
        except httpx.RequestError as exc:
            return JSONResponse(
                status_code=502,
                content={"error": f"AI service unreachable: {exc}"}
            )
        
        try:
            data = response.json()
        except:
            data = response.text
        
        return JSONResponse(
            status_code=response.status_code,
            content=data
        )