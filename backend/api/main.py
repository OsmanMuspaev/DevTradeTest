from fastapi import FastAPI
from router import main_router

app = FastAPI(title="Gateway API")
app.include_router(main_router, prefix="/api")