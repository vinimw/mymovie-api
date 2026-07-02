from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers

app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.APP_DEBUG,
    version="1.0.0",
)

register_exception_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Root"])
def read_root() -> dict[str, str]:
    return {
        "message": settings.APP_NAME,
        "docs_url": "/docs",
    }


app.include_router(api_router, prefix=settings.API_V1_PREFIX)
