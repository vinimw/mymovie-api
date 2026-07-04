from __future__ import annotations

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class TitleMembership(Base):
    __tablename__ = "title_memberships"
    __table_args__ = (
        UniqueConstraint("watched_title_id", "user_email", name="uq_title_memberships_title_user"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    watched_title_id: Mapped[int] = mapped_column(
        ForeignKey("watched_titles.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    user_email: Mapped[str] = mapped_column(String(255), index=True, nullable=False)

    watched_title: Mapped["WatchedTitle"] = relationship(back_populates="memberships")
