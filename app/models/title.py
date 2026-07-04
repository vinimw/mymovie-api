from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import CheckConstraint, DateTime, Enum as SqlEnum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base, utcnow


class TitleType(str, Enum):
    movie = "movie"
    series = "series"


class WatchStatus(str, Enum):
    watched = "watched"
    watching = "watching"
    paused = "paused"
    want_to_watch = "want_to_watch"
    abandoned = "abandoned"


class WatchedTitle(Base):
    __tablename__ = "watched_titles"
    __table_args__ = (
        CheckConstraint("user_rating IS NULL OR user_rating BETWEEN 1 AND 5", name="ck_watched_titles_rating"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    imdb_id: Mapped[str] = mapped_column(String(32), index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    original_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    title_type: Mapped[TitleType] = mapped_column(
        SqlEnum(TitleType, name="title_type_enum", native_enum=False, create_constraint=True),
        index=True,
        nullable=False,
    )
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    poster_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    plot: Mapped[str | None] = mapped_column(Text, nullable=True)
    comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    runtime_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    user_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[WatchStatus] = mapped_column(
        SqlEnum(WatchStatus, name="watch_status_enum", native_enum=False, create_constraint=True),
        index=True,
        nullable=False,
    )
    watched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
    )

    episodes: Mapped[list["WatchedEpisode"]] = relationship(
        back_populates="watched_title",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    memberships: Mapped[list["TitleMembership"]] = relationship(
        back_populates="watched_title",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
