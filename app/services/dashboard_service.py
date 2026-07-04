from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.episode import WatchedEpisode
from app.models.title_membership import TitleMembership
from app.models.title import TitleType, WatchStatus, WatchedTitle
from app.schemas.dashboard import DashboardResponse, DashboardSummary, LastWatchedItem, TotalWatchTimeResponse
from app.utils.time_formatter import format_minutes
from app.core.config import settings


class DashboardService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_dashboard(self, current_user_email: str) -> DashboardResponse:
        current_user = settings.find_configured_admin_user(current_user_email)
        if not current_user:
            raise ValueError("Current user is not configured.")

        other_users = [
            user
            for user in settings.configured_admin_users
            if user.email.lower() != current_user_email.lower()
        ]

        return DashboardResponse(
            current_user=self._build_summary(current_user.email, current_user.display_name),
            other_users=[self._build_summary(user.email, user.display_name) for user in other_users],
            last_watched=self._build_last_watched(),
        )

    def _build_summary(self, user_email: str, display_name: str) -> DashboardSummary:
        movie_minutes = self.db.scalar(
            select(func.coalesce(func.sum(WatchedTitle.runtime_minutes), 0))
            .join(WatchedTitle.memberships)
            .where(
                TitleMembership.user_email == user_email,
                WatchedTitle.title_type == TitleType.movie,
                WatchedTitle.status != WatchStatus.want_to_watch,
                WatchedTitle.watched_at.is_not(None),
            )
        ) or 0
        episode_minutes = self.db.scalar(
            select(func.coalesce(func.sum(WatchedEpisode.runtime_minutes), 0))
            .join(WatchedEpisode.watched_title)
            .join(WatchedTitle.memberships)
            .where(WatchedTitle.status != WatchStatus.want_to_watch)
            .where(TitleMembership.user_email == user_email)
        ) or 0

        movies_count = self.db.scalar(
            select(func.count(func.distinct(WatchedTitle.id)))
            .join(WatchedTitle.memberships)
            .where(
                TitleMembership.user_email == user_email,
                WatchedTitle.title_type == TitleType.movie,
            )
        ) or 0
        series_count = self.db.scalar(
            select(func.count(func.distinct(WatchedTitle.id)))
            .join(WatchedTitle.memberships)
            .where(
                TitleMembership.user_email == user_email,
                WatchedTitle.title_type == TitleType.series,
            )
        ) or 0
        episodes_count = self.db.scalar(
            select(func.count(WatchedEpisode.id))
            .join(WatchedEpisode.watched_title)
            .join(WatchedTitle.memberships)
            .where(TitleMembership.user_email == user_email)
        ) or 0

        average_rating = self.db.scalar(
            select(func.avg(WatchedTitle.user_rating))
            .join(WatchedTitle.memberships)
            .where(TitleMembership.user_email == user_email)
        )
        average_rating_value = round(float(average_rating), 1) if average_rating is not None else None

        total_minutes = int(movie_minutes + episode_minutes)

        return DashboardSummary(
            email=user_email,
            display_name=display_name,
            total_watch_time=TotalWatchTimeResponse(
                total_minutes=total_minutes,
                label=format_minutes(total_minutes),
            ),
            movies_count=int(movies_count),
            series_count=int(series_count),
            episodes_count=int(episodes_count),
            average_rating=average_rating_value,
        )

    def _build_last_watched(self) -> list[LastWatchedItem]:
        title_rows = self.db.scalars(
            select(WatchedTitle)
            .options(selectinload(WatchedTitle.memberships))
            .where(
                WatchedTitle.status != WatchStatus.want_to_watch,
                WatchedTitle.watched_at.is_not(None),
            )
            .order_by(WatchedTitle.watched_at.desc())
            .limit(10)
        ).all()
        episode_rows = self.db.scalars(
            select(WatchedEpisode)
            .options(joinedload(WatchedEpisode.watched_title))
            .join(WatchedEpisode.watched_title)
            .where(
                WatchedTitle.status != WatchStatus.want_to_watch,
                WatchedEpisode.watched_at.is_not(None),
            )
            .order_by(WatchedEpisode.watched_at.desc())
            .limit(10)
        ).all()

        items: list[LastWatchedItem] = []

        for title in title_rows:
            items.append(
                LastWatchedItem(
                    type=title.title_type.value,
                    title_id=title.id,
                    episode_id=None,
                    imdb_id=title.imdb_id,
                    title=title.title,
                    description="Watched movie" if title.title_type == TitleType.movie else "Watched series",
                    poster_url=title.poster_url,
                    owner_display_names=self._owner_display_names(title),
                    watched_at=title.watched_at,
                )
            )

        for episode in episode_rows:
            items.append(
                LastWatchedItem(
                    type="episode",
                    title_id=episode.watched_title.id,
                    episode_id=episode.id,
                    imdb_id=episode.watched_title.imdb_id,
                    title=episode.watched_title.title,
                    description=(
                        f"S{episode.season_number:02d}E{episode.episode_number:02d} - {episode.title}"
                    ),
                    poster_url=episode.watched_title.poster_url,
                    owner_display_names=self._owner_display_names(episode.watched_title),
                    watched_at=episode.watched_at,
                )
            )

        items.sort(key=lambda item: item.watched_at, reverse=True)
        return items[:3]

    @staticmethod
    def _owner_display_names(title: WatchedTitle) -> list[str]:
        if not title.memberships:
            return [user.display_name for user in settings.configured_admin_users]

        owners: list[str] = []
        for membership in title.memberships:
            configured_user = settings.find_configured_admin_user(membership.user_email)
            owners.append(configured_user.display_name if configured_user else membership.user_email)
        return owners
