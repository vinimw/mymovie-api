from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.db.session import SessionLocal
from app.models.title import WatchedTitle
from app.models.title_membership import TitleMembership

app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.APP_DEBUG,
    version="1.0.0",
    docs_url=settings.docs_url,
    redoc_url=settings.redoc_url,
    openapi_url=settings.openapi_url,
)

register_exception_handlers(app)


@app.on_event("startup")
def backfill_title_memberships() -> None:
    db = SessionLocal()
    try:
        titles = list(
            db.scalars(
                select(WatchedTitle)
                .options(selectinload(WatchedTitle.memberships))
            ).unique().all()
        )
        all_user_emails = [user.email for user in settings.configured_admin_users]
        changed = False

        for title in titles:
            if title.memberships:
                continue

            title.memberships = [TitleMembership(user_email=email) for email in all_user_emails]
            db.add(title)
            changed = True

        if changed:
            db.commit()
    finally:
        db.close()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"

    if settings.cookie_secure:
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"

    # Keep local Swagger/ReDoc usable while still hardening normal API responses.
    if request.url.path not in {"/docs", "/redoc", settings.openapi_url}:
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'; base-uri 'none';"

    return response


@app.get("/", tags=["Root"])
def read_root() -> dict[str, str]:
    return {
        "message": settings.APP_NAME,
        "docs_url": settings.docs_url or "disabled",
    }


app.include_router(api_router, prefix=settings.API_V1_PREFIX)
