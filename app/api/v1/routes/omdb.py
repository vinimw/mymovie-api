from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_user
from app.schemas.omdb import OmdbSeasonEpisodes, OmdbTitleDetails, OmdbTitleSearchItem
from app.services.omdb_service import OmdbService

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
async def get_title_details(imdb_id: str) -> OmdbTitleDetails:
    service = OmdbService()
    return await service.get_title_details(imdb_id)


@router.get("/titles/{imdb_id}/episodes", response_model=list[OmdbSeasonEpisodes])
async def get_series_episodes(imdb_id: str) -> list[OmdbSeasonEpisodes]:
    service = OmdbService()
    return await service.get_series_episodes(imdb_id)
