from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import settings

router = APIRouter(tags=["Health"])


@router.get("/health")
def healthcheck(db: Session = Depends(get_db)) -> dict[str, str]:
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is unavailable.",
        ) from exc

    return {
        "status": "ok",
        "database": "ok",
        "omdb_mode": settings.OMDB_PROVIDER_MODE,
        "environment": settings.APP_ENV,
    }
