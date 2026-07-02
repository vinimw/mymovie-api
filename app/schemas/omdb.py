from __future__ import annotations

from pydantic import BaseModel

from app.models.title import TitleType


class OmdbTitleSearchItem(BaseModel):
    imdb_id: str
    title: str
    original_title: str | None = None
    title_type: TitleType
    year: int | None = None
    poster_url: str | None = None
    plot: str | None = None
    runtime_minutes: int | None = None


class OmdbTitleDetails(OmdbTitleSearchItem):
    total_seasons: int | None = None


class OmdbEpisodeItem(BaseModel):
    imdb_episode_id: str
    season_number: int
    episode_number: int
    title: str
    plot: str | None = None
    runtime_minutes: int | None = None


class OmdbSeasonEpisodes(BaseModel):
    season_number: int
    episodes: list[OmdbEpisodeItem]
