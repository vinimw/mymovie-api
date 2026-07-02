from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.schemas.dashboard import DashboardResponse
from app.services.dashboard_service import DashboardService

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=DashboardResponse)
def get_dashboard(db: Session = Depends(get_db)) -> DashboardResponse:
    service = DashboardService(db)
    return service.get_dashboard()
