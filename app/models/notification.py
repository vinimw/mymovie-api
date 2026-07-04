from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, Enum as SqlEnum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base, utcnow


class NotificationKind(str, Enum):
    title_added = "title_added"
    title_deleted = "title_deleted"
    title_status_updated = "title_status_updated"
    title_rating_updated = "title_rating_updated"
    title_comment_added = "title_comment_added"
    title_comment_updated = "title_comment_updated"
    title_comment_removed = "title_comment_removed"
    episodes_added = "episodes_added"
    episode_deleted = "episode_deleted"


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    recipient_email: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    actor_email: Mapped[str] = mapped_column(String(255), nullable=False)
    actor_display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    kind: Mapped[NotificationKind] = mapped_column(
        SqlEnum(NotificationKind, name="notification_kind_enum", native_enum=False, create_constraint=True),
        index=True,
        nullable=False,
    )
    title_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    title_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
