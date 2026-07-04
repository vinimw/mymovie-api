from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.security import AuthenticatedUser
from app.core.config import settings
from app.core.exceptions import BadRequestException, ConflictException, NotFoundException
from app.models.episode import WatchedEpisode
from app.models.title_membership import TitleMembership
from app.models.title import TitleType, WatchStatus, WatchedTitle
from app.schemas.title import WatchedEpisodeCreate, WatchedTitleCreate, WatchedTitleUpdate


class TitleRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_titles(
        self,
        *,
        current_user: AuthenticatedUser,
        q: str | None = None,
        title_type: TitleType | None = None,
        status: WatchStatus | None = None,
        collection: str = "all",
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[WatchedTitle], int]:
        stmt = select(WatchedTitle).options(
            selectinload(WatchedTitle.episodes),
            selectinload(WatchedTitle.memberships),
        )
        stmt = self._apply_collection_filter(
            stmt,
            current_user=current_user,
            collection=collection,
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

        total = self.db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
        items = list(
            self.db.scalars(
                stmt.order_by(WatchedTitle.watched_at.desc().nullslast(), WatchedTitle.created_at.desc())
                .offset(offset)
                .limit(limit)
            ).unique().all()
        )
        return items, int(total)

    def get_title_or_404(self, title_id: int) -> WatchedTitle:
        stmt = (
            select(WatchedTitle)
            .options(selectinload(WatchedTitle.episodes), selectinload(WatchedTitle.memberships))
            .where(WatchedTitle.id == title_id)
        )
        title = self.db.scalar(stmt)
        if not title:
            raise NotFoundException("Title not found.")
        return title

    def create_title(self, payload: WatchedTitleCreate, current_user: AuthenticatedUser) -> WatchedTitle:
        owner_emails = self._owner_emails_for_scope(payload.ownership_scope, current_user)
        existing_title = self._find_duplicate_for_scope(payload.imdb_id, owner_emails)
        if existing_title:
            raise ConflictException("This title already exists for the selected list.")

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
        self._set_memberships(title, owner_emails)

        for episode in self._normalize_episode_payload(payload.episodes):
            title.episodes.append(self._episode_model_from_payload(episode))

        self.db.add(title)

        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise ConflictException("A watched title with this external id already exists.") from exc

        return self.get_title_or_404(title.id)

    def update_title(self, title_id: int, payload: WatchedTitleUpdate, current_user: AuthenticatedUser) -> WatchedTitle:
        title = self.get_title_or_404(title_id)
        self.ensure_can_edit(title, current_user)

        if "ownership_scope" in payload.model_fields_set and payload.ownership_scope is not None:
            next_owner_emails = self._owner_emails_for_scope(payload.ownership_scope, current_user)
            existing_title = self._find_duplicate_for_scope(title.imdb_id, next_owner_emails)
            if existing_title and existing_title.id != title.id:
                raise ConflictException("This title already exists for the selected list.")
            self._set_memberships(title, next_owner_emails)

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
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise ConflictException("This title could not be updated because of a conflicting ownership record.") from exc
        return self.get_title_or_404(title.id)

    def delete_title(self, title_id: int, current_user: AuthenticatedUser) -> None:
        title = self.get_title_or_404(title_id)
        self.ensure_can_edit(title, current_user)
        self.db.delete(title)
        self.db.commit()

    def add_episodes(
        self,
        title_id: int,
        episodes: Iterable[WatchedEpisodeCreate],
        current_user: AuthenticatedUser,
    ) -> WatchedTitle:
        title = self.get_title_or_404(title_id)
        self.ensure_can_edit(title, current_user)
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

    def delete_episode(self, episode_id: int, current_user: AuthenticatedUser) -> None:
        episode = self.get_episode_or_404(episode_id)
        self.ensure_can_edit(episode.watched_title, current_user)

        self.db.delete(episode)
        self.db.commit()

    def get_episode_or_404(self, episode_id: int) -> WatchedEpisode:
        stmt = (
            select(WatchedEpisode)
            .options(joinedload(WatchedEpisode.watched_title))
            .where(WatchedEpisode.id == episode_id)
        )
        episode = self.db.scalar(stmt)
        if not episode:
            raise NotFoundException("Episode not found.")
        return episode

    def ensure_can_edit(self, title: WatchedTitle, current_user: AuthenticatedUser) -> None:
        owner_emails = self.get_owner_emails(title)
        if current_user.email not in owner_emails:
            raise BadRequestException("You can only edit titles that belong to your own list.")

    def get_owner_emails(self, title: WatchedTitle) -> list[str]:
        if title.memberships:
            return sorted({membership.user_email for membership in title.memberships})
        return sorted(user.email for user in settings.configured_admin_users)

    def is_shared(self, title: WatchedTitle) -> bool:
        return len(self.get_owner_emails(title)) > 1

    def ownership_scope(self, title: WatchedTitle) -> str:
        return "shared" if self.is_shared(title) else "personal"

    def _owner_emails_for_scope(self, ownership_scope: str, current_user: AuthenticatedUser) -> list[str]:
        if ownership_scope == "shared":
            return sorted(user.email for user in settings.configured_admin_users)
        return [current_user.email]

    def _set_memberships(self, title: WatchedTitle, owner_emails: list[str]) -> None:
        desired_emails = sorted(set(owner_emails))
        existing_by_email = {membership.user_email: membership for membership in title.memberships}

        title.memberships[:] = [
            membership
            for membership in title.memberships
            if membership.user_email in desired_emails
        ]

        for email in desired_emails:
            if email not in existing_by_email:
                title.memberships.append(TitleMembership(user_email=email))

    def _find_duplicate_for_scope(self, imdb_id: str, owner_emails: list[str]) -> WatchedTitle | None:
        candidate_titles = list(
            self.db.scalars(
                select(WatchedTitle)
                .options(selectinload(WatchedTitle.memberships))
                .where(WatchedTitle.imdb_id == imdb_id)
            ).unique().all()
        )

        normalized_scope = sorted(set(owner_emails))
        for title in candidate_titles:
            if self.get_owner_emails(title) == normalized_scope:
                return title
        return None

    def _apply_collection_filter(
        self,
        stmt,
        *,
        current_user: AuthenticatedUser,
        collection: str,
    ):
        shared_ids_subquery = (
            select(TitleMembership.watched_title_id)
            .group_by(TitleMembership.watched_title_id)
            .having(func.count(TitleMembership.id) > 1)
        )
        personal_ids_subquery = (
            select(TitleMembership.watched_title_id)
            .group_by(TitleMembership.watched_title_id)
            .having(func.count(TitleMembership.id) == 1)
        )

        if collection == "shared":
            return stmt.where(WatchedTitle.id.in_(shared_ids_subquery))

        if collection == "mine":
            return stmt.where(
                WatchedTitle.id.in_(personal_ids_subquery),
                WatchedTitle.id.in_(
                    select(TitleMembership.watched_title_id).where(
                        TitleMembership.user_email == current_user.email,
                    )
                ),
            )

        if collection == "other":
            other_emails = settings.other_user_emails(current_user.email)
            return stmt.where(
                WatchedTitle.id.in_(personal_ids_subquery),
                WatchedTitle.id.in_(
                    select(TitleMembership.watched_title_id).where(
                        TitleMembership.user_email.in_(other_emails),
                    )
                ),
            )

        return stmt

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
