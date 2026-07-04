from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.core.security import AuthenticatedUser
from app.models.title import TitleType, WatchStatus
from app.repositories.title_repository import TitleRepository
from app.schemas.title import (
    WatchedEpisodeBulkCreate,
    WatchedTitleCreate,
    WatchedTitleListItem,
    WatchedTitleListResponse,
    WatchedTitleResponse,
    WatchedTitleUpdate,
)
from app.services.notification_service import EpisodeSnapshot, NotificationService, TitleSnapshot

router = APIRouter(
    prefix="/titles",
    tags=["Titles"],
)


def serialize_title(title, current_user: AuthenticatedUser, repository: TitleRepository) -> WatchedTitleResponse:
    owners = []
    for owner_email in repository.get_owner_emails(title):
        configured_user = settings.find_configured_admin_user(owner_email)
        owners.append(
            {
                "email": owner_email,
                "display_name": configured_user.display_name if configured_user else owner_email,
            }
        )

    payload = {
        "id": title.id,
        "imdb_id": title.imdb_id,
        "title": title.title,
        "original_title": title.original_title,
        "title_type": title.title_type,
        "year": title.year,
        "poster_url": title.poster_url,
        "plot": title.plot,
        "comments": title.comments,
        "runtime_minutes": title.runtime_minutes,
        "user_rating": title.user_rating,
        "status": title.status,
        "watched_at": title.watched_at,
        "created_at": title.created_at,
        "updated_at": title.updated_at,
        "owners": owners,
        "ownership_scope": repository.ownership_scope(title),
        "is_shared": repository.is_shared(title),
        "can_edit": current_user.email in repository.get_owner_emails(title),
        "episodes": [
            {
                "id": episode.id,
                "watched_title_id": episode.watched_title_id,
                "imdb_episode_id": episode.imdb_episode_id,
                "season_number": episode.season_number,
                "episode_number": episode.episode_number,
                "title": episode.title,
                "plot": episode.plot,
                "runtime_minutes": episode.runtime_minutes,
                "watched_at": episode.watched_at,
                "created_at": episode.created_at,
            }
            for episode in title.episodes
        ],
    }
    return WatchedTitleResponse.model_validate(payload)


@router.get("", response_model=WatchedTitleListResponse)
def list_titles(
    q: str | None = Query(None),
    title_type: TitleType | None = Query(None),
    status_filter: WatchStatus | None = Query(None, alias="status"),
    collection: str = Query("all", pattern="^(all|shared|mine|other)$"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WatchedTitleListResponse:
    repository = TitleRepository(db)
    titles, total = repository.list_titles(
        current_user=current_user,
        q=q,
        title_type=title_type,
        status=status_filter,
        collection=collection,
        limit=limit,
        offset=offset,
    )
    return WatchedTitleListResponse(
        items=[
            WatchedTitleListItem.model_validate(serialize_title(title, current_user, repository).model_dump())
            for title in titles
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=WatchedTitleResponse, status_code=status.HTTP_201_CREATED)
def create_title(
    payload: WatchedTitleCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WatchedTitleResponse:
    repository = TitleRepository(db)
    title = repository.create_title(payload, current_user)
    NotificationService(db).notify_title_created(current_user, title)
    return serialize_title(title, current_user, repository)


@router.get("/{title_id}", response_model=WatchedTitleResponse)
def get_title(
    title_id: int,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WatchedTitleResponse:
    repository = TitleRepository(db)
    title = repository.get_title_or_404(title_id)
    return serialize_title(title, current_user, repository)


@router.patch("/{title_id}", response_model=WatchedTitleResponse)
def update_title(
    title_id: int,
    payload: WatchedTitleUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WatchedTitleResponse:
    repository = TitleRepository(db)
    before = TitleSnapshot.from_model(repository.get_title_or_404(title_id))
    title = repository.update_title(title_id, payload, current_user)
    NotificationService(db).notify_title_updates(current_user, before, title)
    return serialize_title(title, current_user, repository)


@router.delete("/{title_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_title(
    title_id: int,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    repository = TitleRepository(db)
    snapshot = TitleSnapshot.from_model(repository.get_title_or_404(title_id))
    repository.delete_title(title_id, current_user)
    NotificationService(db).notify_title_deleted(current_user, snapshot)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{title_id}/episodes", response_model=WatchedTitleResponse)
def add_title_episodes(
    title_id: int,
    payload: WatchedEpisodeBulkCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WatchedTitleResponse:
    repository = TitleRepository(db)
    before = TitleSnapshot.from_model(repository.get_title_or_404(title_id))
    title = repository.add_episodes(title_id, payload.episodes, current_user)
    added_count = len([episode for episode in title.episodes if episode.imdb_episode_id not in before.episode_ids])
    NotificationService(db).notify_episodes_added(current_user, title, added_count)
    return serialize_title(title, current_user, repository)


@router.delete("/episodes/{episode_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_episode(
    episode_id: int,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    repository = TitleRepository(db)
    episode_snapshot = EpisodeSnapshot.from_model(repository.get_episode_or_404(episode_id))
    repository.delete_episode(episode_id, current_user)
    NotificationService(db).notify_episode_deleted(current_user, episode_snapshot)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
