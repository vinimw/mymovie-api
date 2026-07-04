from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import AuthenticatedUser
from app.models.episode import WatchedEpisode
from app.models.notification import Notification, NotificationKind
from app.models.title import TitleType, WatchStatus, WatchedTitle


@dataclass(frozen=True, slots=True)
class TitleSnapshot:
    id: int
    title: str
    title_type: TitleType
    status: WatchStatus
    user_rating: int | None
    comments: str | None
    episode_ids: frozenset[str]

    @classmethod
    def from_model(cls, title: WatchedTitle) -> "TitleSnapshot":
        return cls(
            id=title.id,
            title=title.title,
            title_type=title.title_type,
            status=title.status,
            user_rating=title.user_rating,
            comments=title.comments,
            episode_ids=frozenset(episode.imdb_episode_id for episode in title.episodes),
        )


@dataclass(frozen=True, slots=True)
class EpisodeSnapshot:
    id: int
    title_id: int
    title_name: str
    season_number: int
    episode_number: int
    episode_title: str

    @classmethod
    def from_model(cls, episode: WatchedEpisode) -> "EpisodeSnapshot":
        return cls(
            id=episode.id,
            title_id=episode.watched_title_id,
            title_name=episode.watched_title.title,
            season_number=episode.season_number,
            episode_number=episode.episode_number,
            episode_title=episode.title,
        )

    @property
    def episode_label(self) -> str:
        season = str(self.season_number).zfill(2)
        episode = str(self.episode_number).zfill(2)
        return f"S{season}E{episode} - {self.episode_title}"


class NotificationService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_notifications(
        self,
        *,
        recipient_email: str,
        limit: int,
        offset: int,
    ) -> tuple[list[Notification], int]:
        items = list(
            self.db.scalars(
                select(Notification)
                .where(Notification.recipient_email == recipient_email)
                .order_by(Notification.created_at.desc(), Notification.id.desc())
                .offset(offset)
                .limit(limit)
            )
        )
        total = self.db.scalar(
            select(func.count(Notification.id)).where(Notification.recipient_email == recipient_email)
        ) or 0
        return items, total

    def count_unread(self, recipient_email: str) -> int:
        return self.db.scalar(
            select(func.count(Notification.id)).where(
                Notification.recipient_email == recipient_email,
                Notification.is_read.is_(False),
            )
        ) or 0

    def mark_all_as_read(self, recipient_email: str) -> int:
        unread_notifications = list(
            self.db.scalars(
                select(Notification).where(
                    Notification.recipient_email == recipient_email,
                    Notification.is_read.is_(False),
                )
            )
        )
        if not unread_notifications:
            return 0

        now = self._now()
        for notification in unread_notifications:
            notification.is_read = True
            notification.read_at = now
            self.db.add(notification)

        self.db.commit()
        return len(unread_notifications)

    def notify_title_created(self, actor: AuthenticatedUser, title: WatchedTitle) -> None:
        self._create_for_other_users(
            actor=actor,
            kind=NotificationKind.title_added,
            title_id=title.id,
            title_name=title.title,
            message=f"{actor.display_name} added the {self._title_label(title.title_type)} {title.title}.",
        )

        if title.comments:
            self._create_for_other_users(
                actor=actor,
                kind=NotificationKind.title_comment_added,
                title_id=title.id,
                title_name=title.title,
                message=f"{actor.display_name} added a comment on {title.title}.",
            )

    def notify_title_deleted(self, actor: AuthenticatedUser, title: TitleSnapshot) -> None:
        self._create_for_other_users(
            actor=actor,
            kind=NotificationKind.title_deleted,
            title_name=title.title,
            message=f"{actor.display_name} deleted the {self._title_label(title.title_type)} {title.title}.",
        )

    def notify_title_updates(
        self,
        actor: AuthenticatedUser,
        before: TitleSnapshot,
        after: WatchedTitle,
    ) -> None:
        if before.status != after.status:
            self._create_for_other_users(
                actor=actor,
                kind=NotificationKind.title_status_updated,
                title_id=after.id,
                title_name=after.title,
                message=(
                    f"{actor.display_name} changed the status of {after.title} to "
                    f"{self._status_label(after.status)}."
                ),
            )

        if before.user_rating != after.user_rating:
            if after.user_rating is None:
                message = f"{actor.display_name} cleared the rating for {after.title}."
            else:
                stars = "star" if after.user_rating == 1 else "stars"
                message = f"{actor.display_name} updated the rating of {after.title} to {after.user_rating} {stars}."

            self._create_for_other_users(
                actor=actor,
                kind=NotificationKind.title_rating_updated,
                title_id=after.id,
                title_name=after.title,
                message=message,
            )

        if before.comments != after.comments:
            if before.comments and after.comments:
                kind = NotificationKind.title_comment_updated
                message = f"{actor.display_name} updated the comment on {after.title}."
            elif after.comments:
                kind = NotificationKind.title_comment_added
                message = f"{actor.display_name} added a comment on {after.title}."
            else:
                kind = NotificationKind.title_comment_removed
                message = f"{actor.display_name} removed the comment from {after.title}."

            self._create_for_other_users(
                actor=actor,
                kind=kind,
                title_id=after.id,
                title_name=after.title,
                message=message,
            )

    def notify_episodes_added(self, actor: AuthenticatedUser, title: WatchedTitle, added_count: int) -> None:
        if added_count <= 0:
            return

        label = "episode" if added_count == 1 else "episodes"
        self._create_for_other_users(
            actor=actor,
            kind=NotificationKind.episodes_added,
            title_id=title.id,
            title_name=title.title,
            message=f"{actor.display_name} added {added_count} {label} to {title.title}.",
        )

    def notify_episode_deleted(self, actor: AuthenticatedUser, episode: EpisodeSnapshot) -> None:
        self._create_for_other_users(
            actor=actor,
            kind=NotificationKind.episode_deleted,
            title_id=episode.title_id,
            title_name=episode.title_name,
            message=f"{actor.display_name} removed {episode.episode_label} from {episode.title_name}.",
        )

    def _create_for_other_users(
        self,
        *,
        actor: AuthenticatedUser,
        kind: NotificationKind,
        message: str,
        title_id: int | None = None,
        title_name: str | None = None,
    ) -> None:
        recipient_emails = self._recipient_emails(actor.email)
        if not recipient_emails:
            return

        created_at = self._now()
        for recipient_email in recipient_emails:
            self.db.add(
                Notification(
                    recipient_email=recipient_email,
                    actor_email=actor.email,
                    actor_display_name=actor.display_name,
                    kind=kind,
                    title_id=title_id,
                    title_name=title_name,
                    message=message,
                    is_read=False,
                    read_at=None,
                    created_at=created_at,
                )
            )

        self.db.commit()

    @staticmethod
    def _title_label(title_type: TitleType) -> str:
        return "movie" if title_type == TitleType.movie else "series"

    @staticmethod
    def _status_label(status: WatchStatus) -> str:
        if status == WatchStatus.want_to_watch:
            return "Not watched yet"
        return status.value.replace("_", " ").title()

    @staticmethod
    def _recipient_emails(actor_email: str) -> list[str]:
        from app.core.config import settings

        return settings.other_user_emails(actor_email)

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)
