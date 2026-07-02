from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.episode import WatchedEpisode
from app.models.title import TitleType, WatchStatus, WatchedTitle
from app.schemas.dashboard import DashboardResponse, LastWatchedItem, TotalWatchTimeResponse
from app.utils.time_formatter import format_minutes


class DashboardService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_dashboard(self) -> DashboardResponse:
        movie_minutes = self.db.scalar(
            select(func.coalesce(func.sum(WatchedTitle.runtime_minutes), 0)).where(
                WatchedTitle.title_type == TitleType.movie,
                WatchedTitle.status != WatchStatus.want_to_watch,
                WatchedTitle.watched_at.is_not(None),
            )
        ) or 0
        episode_minutes = self.db.scalar(
            select(func.coalesce(func.sum(WatchedEpisode.runtime_minutes), 0))
            .join(WatchedEpisode.watched_title)
            .where(WatchedTitle.status != WatchStatus.want_to_watch)
        ) or 0

        movies_count = self.db.scalar(
            select(func.count(WatchedTitle.id)).where(WatchedTitle.title_type == TitleType.movie)
        ) or 0
        series_count = self.db.scalar(
            select(func.count(WatchedTitle.id)).where(WatchedTitle.title_type == TitleType.series)
        ) or 0
        episodes_count = self.db.scalar(select(func.count(WatchedEpisode.id))) or 0

        average_rating = self.db.scalar(select(func.avg(WatchedTitle.user_rating)))
        average_rating_value = round(float(average_rating), 1) if average_rating is not None else None

        total_minutes = int(movie_minutes + episode_minutes)

        return DashboardResponse(
            total_watch_time=TotalWatchTimeResponse(
                total_minutes=total_minutes,
                label=format_minutes(total_minutes),
            ),
            movies_count=int(movies_count),
            series_count=int(series_count),
            episodes_count=int(episodes_count),
            average_rating=average_rating_value,
            last_watched=self._build_last_watched(),
        )

    def _build_last_watched(self) -> list[LastWatchedItem]:
        title_rows = self.db.scalars(
            select(WatchedTitle)
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
                    watched_at=episode.watched_at,
                )
            )

        items.sort(key=lambda item: item.watched_at, reverse=True)
        return items[:3]
