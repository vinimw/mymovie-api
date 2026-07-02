from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.title import TitleType, WatchStatus
from app.repositories.title_repository import TitleRepository
from app.schemas.title import (
    WatchedEpisodeBulkCreate,
    WatchedTitleCreate,
    WatchedTitleListItem,
    WatchedTitleResponse,
    WatchedTitleUpdate,
)

router = APIRouter(
    prefix="/titles",
    tags=["Titles"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=list[WatchedTitleListItem])
def list_titles(
    q: str | None = Query(None),
    title_type: TitleType | None = Query(None),
    status_filter: WatchStatus | None = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
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
    db: Session = Depends(get_db),
) -> WatchedTitleResponse:
    repository = TitleRepository(db)
    title = repository.create_title(payload)
    return WatchedTitleResponse.model_validate(title)


@router.get("/{title_id}", response_model=WatchedTitleResponse)
def get_title(title_id: int, db: Session = Depends(get_db)) -> WatchedTitleResponse:
    repository = TitleRepository(db)
    title = repository.get_title_or_404(title_id)
    return WatchedTitleResponse.model_validate(title)


@router.patch("/{title_id}", response_model=WatchedTitleResponse)
def update_title(
    title_id: int,
    payload: WatchedTitleUpdate,
    db: Session = Depends(get_db),
) -> WatchedTitleResponse:
    repository = TitleRepository(db)
    title = repository.update_title(title_id, payload)
    return WatchedTitleResponse.model_validate(title)


@router.delete("/{title_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_title(title_id: int, db: Session = Depends(get_db)) -> Response:
    repository = TitleRepository(db)
    repository.delete_title(title_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{title_id}/episodes", response_model=WatchedTitleResponse)
def add_title_episodes(
    title_id: int,
    payload: WatchedEpisodeBulkCreate,
    db: Session = Depends(get_db),
) -> WatchedTitleResponse:
    repository = TitleRepository(db)
    title = repository.add_episodes(title_id, payload.episodes)
    return WatchedTitleResponse.model_validate(title)


@router.delete("/episodes/{episode_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_episode(episode_id: int, db: Session = Depends(get_db)) -> Response:
    repository = TitleRepository(db)
    repository.delete_episode(episode_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
