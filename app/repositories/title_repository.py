from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.core.exceptions import BadRequestException, ConflictException, NotFoundException
from app.models.episode import WatchedEpisode
from app.models.title import TitleType, WatchStatus, WatchedTitle
from app.schemas.title import WatchedEpisodeCreate, WatchedTitleCreate, WatchedTitleUpdate


class TitleRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_titles(
        self,
        *,
        q: str | None = None,
        title_type: TitleType | None = None,
        status: WatchStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[WatchedTitle]:
        stmt = (
            select(WatchedTitle)
            .options(selectinload(WatchedTitle.episodes))
            .order_by(WatchedTitle.watched_at.desc().nullslast(), WatchedTitle.created_at.desc())
            .offset(offset)
            .limit(limit)
        )

        if q:
            pattern = f"%{q.strip()}%"
            stmt = stmt.where(
                or_(
                    WatchedTitle.title.ilike(pattern),
                    WatchedTitle.original_title.ilike(pattern),
                )
            )

        if title_type:
            stmt = stmt.where(WatchedTitle.title_type == title_type)

        if status:
            stmt = stmt.where(WatchedTitle.status == status)

        return list(self.db.scalars(stmt).unique().all())

    def get_title_or_404(self, title_id: int) -> WatchedTitle:
        stmt = (
            select(WatchedTitle)
            .options(selectinload(WatchedTitle.episodes))
            .where(WatchedTitle.id == title_id)
        )
        title = self.db.scalar(stmt)
        if not title:
            raise NotFoundException("Title not found.")
        return title

    def create_title(self, payload: WatchedTitleCreate) -> WatchedTitle:
        title = WatchedTitle(
            imdb_id=payload.imdb_id,
            title=payload.title,
            original_title=payload.original_title,
            title_type=payload.title_type,
            year=payload.year,
            poster_url=payload.poster_url,
            plot=payload.plot,
            comments=payload.comments,
            runtime_minutes=payload.runtime_minutes,
            user_rating=payload.user_rating,
            status=payload.status,
            watched_at=payload.watched_at or self._default_watched_at(payload.status),
        )

        for episode in self._normalize_episode_payload(payload.episodes):
            title.episodes.append(self._episode_model_from_payload(episode))

        self.db.add(title)

        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise ConflictException("A watched title with this external id already exists.") from exc

        return self.get_title_or_404(title.id)

    def update_title(self, title_id: int, payload: WatchedTitleUpdate) -> WatchedTitle:
        title = self.get_title_or_404(title_id)

        if payload.user_rating is not None:
            title.user_rating = payload.user_rating
        if payload.status is not None:
            title.status = payload.status
            if payload.status == WatchStatus.want_to_watch:
                title.watched_at = None
            elif title.watched_at is None:
                title.watched_at = self._now()
        if "comments" in payload.model_fields_set:
            title.comments = payload.comments

        self.db.add(title)
        self.db.commit()
        return self.get_title_or_404(title.id)

    def delete_title(self, title_id: int) -> None:
        title = self.get_title_or_404(title_id)
        self.db.delete(title)
        self.db.commit()

    def add_episodes(self, title_id: int, episodes: Iterable[WatchedEpisodeCreate]) -> WatchedTitle:
        title = self.get_title_or_404(title_id)
        if title.title_type != TitleType.series:
            raise BadRequestException("Episodes can only be added to series.")

        existing_ids = {episode.imdb_episode_id for episode in title.episodes}
        for episode in self._normalize_episode_payload(episodes):
            if episode.imdb_episode_id in existing_ids:
                continue
            title.episodes.append(self._episode_model_from_payload(episode))
            existing_ids.add(episode.imdb_episode_id)

        self.db.add(title)
        self.db.commit()
        return self.get_title_or_404(title.id)

    def delete_episode(self, episode_id: int) -> None:
        episode = self.db.get(WatchedEpisode, episode_id)
        if not episode:
            raise NotFoundException("Episode not found.")

        self.db.delete(episode)
        self.db.commit()

    def _episode_model_from_payload(self, payload: WatchedEpisodeCreate) -> WatchedEpisode:
        return WatchedEpisode(
            imdb_episode_id=payload.imdb_episode_id,
            season_number=payload.season_number,
            episode_number=payload.episode_number,
            title=payload.title,
            plot=payload.plot,
            runtime_minutes=payload.runtime_minutes or settings.DEFAULT_EPISODE_RUNTIME_MINUTES,
            watched_at=payload.watched_at or self._now(),
        )

    def _normalize_episode_payload(
        self,
        episodes: Iterable[WatchedEpisodeCreate],
    ) -> list[WatchedEpisodeCreate]:
        normalized: list[WatchedEpisodeCreate] = []
        seen_ids: set[str] = set()

        for episode in episodes:
            if episode.imdb_episode_id in seen_ids:
                continue
            seen_ids.add(episode.imdb_episode_id)
            normalized.append(episode)

        return normalized

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    def _default_watched_at(self, status: WatchStatus) -> datetime | None:
        if status == WatchStatus.want_to_watch:
            return None
        return self._now()
