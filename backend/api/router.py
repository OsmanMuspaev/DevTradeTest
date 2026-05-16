from fastapi import APIRouter
from endpoints import ai, core, health, users, sandbox

main_router = APIRouter()

main_router.include_router(core.router, prefix="/core", tags=["Core"])
main_router.include_router(ai.router, prefix="/ai", tags=["AI"])
main_router.include_router(health.router, prefix="/health", tags=["Health"])
main_router.include_router(users.router, prefix="/users", tags=["Users"])
main_router.include_router(sandbox.router, prefix="/sandbox", tags=["Sandbox"])
