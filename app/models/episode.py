from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base, utcnow


class WatchedEpisode(Base):
    __tablename__ = "watched_episodes"
    __table_args__ = (
        UniqueConstraint(
            "watched_title_id",
            "imdb_episode_id",
            name="uq_watched_episodes_title_episode",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    watched_title_id: Mapped[int] = mapped_column(
        ForeignKey("watched_titles.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    imdb_episode_id: Mapped[str] = mapped_column(String(32), nullable=False)
    season_number: Mapped[int] = mapped_column(Integer, nullable=False)
    episode_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    plot: Mapped[str | None] = mapped_column(Text, nullable=True)
    runtime_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    watched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    watched_title: Mapped["WatchedTitle"] = relationship(back_populates="episodes")
