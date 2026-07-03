from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, Response, status

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.exceptions import AuthenticationException
from app.core.security import create_access_token, verify_password
from app.schemas.auth import LoginRequest, LoginResponse, MeResponse

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, response: Response) -> LoginResponse:
    credentials_are_valid = payload.email.lower() == settings.ADMIN_EMAIL.lower() and verify_password(
        payload.password,
        settings.ADMIN_PASSWORD_HASH,
    )

    if not credentials_are_valid:
        raise AuthenticationException("Invalid email or password.")

    token = create_access_token(
        subject=settings.ADMIN_EMAIL,
        expires_delta=timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    response.set_cookie(
        key=settings.AUTH_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite=settings.cookie_samesite,
        secure=settings.cookie_secure,
        max_age=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )

    return LoginResponse()


@router.post("/logout", status_code=status.HTTP_200_OK)
def logout(response: Response) -> dict[str, str]:
    response.delete_cookie(
        key=settings.AUTH_COOKIE_NAME,
        path="/",
        httponly=True,
        samesite=settings.cookie_samesite,
        secure=settings.cookie_secure,
    )
    return {"message": "Logged out successfully."}


@router.get("/me", response_model=MeResponse)
def me(current_user=Depends(get_current_user)) -> MeResponse:
    return MeResponse(email=current_user.email)
