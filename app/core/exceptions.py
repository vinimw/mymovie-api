from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class AppException(Exception):
    status_code = 400
    detail = "Application error."

    def __init__(self, detail: str | None = None) -> None:
        if detail:
            self.detail = detail


class AuthenticationException(AppException):
    status_code = 401
    detail = "Authentication failed."


class NotFoundException(AppException):
    status_code = 404
    detail = "Resource not found."


class ConflictException(AppException):
    status_code = 409
    detail = "Resource conflict."


class BadRequestException(AppException):
    status_code = 400
    detail = "Bad request."


class ProviderNotImplementedException(AppException):
    status_code = 503
    detail = "OMDb provider is not configured yet."


class UpstreamServiceException(AppException):
    status_code = 502
    detail = "External provider request failed."


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def handle_app_exception(_: Request, exc: AppException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )
