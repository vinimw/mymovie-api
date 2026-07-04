from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.notification import NotificationKind


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    actor_email: str
    actor_display_name: str
    kind: NotificationKind
    title_id: int | None = None
    title_name: str | None = None
    message: str
    is_read: bool
    read_at: datetime | None = None
    created_at: datetime


class NotificationListResponse(BaseModel):
    items: list[NotificationResponse]
    total: int
    limit: int
    offset: int
    unread_count: int


class NotificationUnreadCountResponse(BaseModel):
    unread_count: int


class NotificationsReadResponse(BaseModel):
    marked_read_count: int
