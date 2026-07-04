from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.security import AuthenticatedUser
from app.schemas.notification import (
    NotificationListResponse,
    NotificationResponse,
    NotificationsReadResponse,
    NotificationUnreadCountResponse,
)
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=NotificationListResponse)
def list_notifications(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NotificationListResponse:
    service = NotificationService(db)
    items, total = service.list_notifications(
        recipient_email=current_user.email,
        limit=limit,
        offset=offset,
    )
    unread_count = service.count_unread(current_user.email)
    return NotificationListResponse(
        items=[NotificationResponse.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
        unread_count=unread_count,
    )


@router.get("/unread-count", response_model=NotificationUnreadCountResponse)
def get_unread_notification_count(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NotificationUnreadCountResponse:
    service = NotificationService(db)
    return NotificationUnreadCountResponse(unread_count=service.count_unread(current_user.email))


@router.post("/read-all", response_model=NotificationsReadResponse)
def mark_all_notifications_as_read(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NotificationsReadResponse:
    service = NotificationService(db)
    marked_read_count = service.mark_all_as_read(current_user.email)
    return NotificationsReadResponse(marked_read_count=marked_read_count)
