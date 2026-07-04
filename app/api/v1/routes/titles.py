from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.security import AuthenticatedUser
from app.models.title import TitleType, WatchStatus
from app.repositories.title_repository import TitleRepository
from app.schemas.title import (
    WatchedEpisodeBulkCreate,
    WatchedTitleCreate,
    WatchedTitleListItem,
    WatchedTitleResponse,
    WatchedTitleUpdate,
)
from app.services.notification_service import EpisodeSnapshot, NotificationService, TitleSnapshot

router = APIRouter(
    prefix="/titles",
    tags=["Titles"],
)


@router.get("", response_model=list[WatchedTitleListItem])
def list_titles(
    q: str | None = Query(None),
    title_type: TitleType | None = Query(None),
    status_filter: WatchStatus | None = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[WatchedTitleListItem]:
    repository = TitleRepository(db)
    titles = repository.list_titles(
        q=q,
        title_type=title_type,
        status=status_filter,
        limit=limit,
        offset=offset,
    )
    return [WatchedTitleListItem.model_validate(title) for title in titles]


@router.post("", response_model=WatchedTitleResponse, status_code=status.HTTP_201_CREATED)
def create_title(
    payload: WatchedTitleCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WatchedTitleResponse:
    repository = TitleRepository(db)
    title = repository.create_title(payload)
    NotificationService(db).notify_title_created(current_user, title)
    return WatchedTitleResponse.model_validate(title)


@router.get("/{title_id}", response_model=WatchedTitleResponse)
def get_title(
    title_id: int,
    _: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WatchedTitleResponse:
    repository = TitleRepository(db)
    title = repository.get_title_or_404(title_id)
    return WatchedTitleResponse.model_validate(title)


@router.patch("/{title_id}", response_model=WatchedTitleResponse)
def update_title(
    title_id: int,
    payload: WatchedTitleUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WatchedTitleResponse:
    repository = TitleRepository(db)
    before = TitleSnapshot.from_model(repository.get_title_or_404(title_id))
    title = repository.update_title(title_id, payload)
    NotificationService(db).notify_title_updates(current_user, before, title)
    return WatchedTitleResponse.model_validate(title)


@router.delete("/{title_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_title(
    title_id: int,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    repository = TitleRepository(db)
    snapshot = TitleSnapshot.from_model(repository.get_title_or_404(title_id))
    repository.delete_title(title_id)
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
    title = repository.add_episodes(title_id, payload.episodes)
    added_count = len([episode for episode in title.episodes if episode.imdb_episode_id not in before.episode_ids])
    NotificationService(db).notify_episodes_added(current_user, title, added_count)
    return WatchedTitleResponse.model_validate(title)


@router.delete("/episodes/{episode_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_episode(
    episode_id: int,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    repository = TitleRepository(db)
    episode_snapshot = EpisodeSnapshot.from_model(repository.get_episode_or_404(episode_id))
    repository.delete_episode(episode_id)
    NotificationService(db).notify_episode_deleted(current_user, episode_snapshot)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
