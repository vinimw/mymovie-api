from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from app.api.deps import get_current_user
from app.schemas.omdb import OmdbSeasonEpisodes, OmdbTitleDetails, OmdbTitleSearchItem
from app.services.omdb_service import OmdbService

ImdbIdPath = Annotated[str, Path(pattern=r"^tt\d{7,10}$")]

router = APIRouter(
    prefix="/omdb",
    tags=["OMDb"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/search", response_model=list[OmdbTitleSearchItem])
async def search_titles(q: str = Query(..., min_length=1)) -> list[OmdbTitleSearchItem]:
    service = OmdbService()
    return await service.search_titles(q)


@router.get("/titles/{imdb_id}", response_model=OmdbTitleDetails)
async def get_title_details(imdb_id: ImdbIdPath) -> OmdbTitleDetails:
    service = OmdbService()
    return await service.get_title_details(imdb_id)


@router.get("/titles/{imdb_id}/episodes", response_model=list[OmdbSeasonEpisodes])
async def get_series_episodes(imdb_id: ImdbIdPath) -> list[OmdbSeasonEpisodes]:
    service = OmdbService()
    return await service.get_series_episodes(imdb_id)
