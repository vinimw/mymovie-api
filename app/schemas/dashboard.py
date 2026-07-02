from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class TotalWatchTimeResponse(BaseModel):
    total_minutes: int
    label: str


class LastWatchedItem(BaseModel):
    type: Literal["movie", "series", "episode"]
    title_id: int
    episode_id: int | None = None
    imdb_id: str
    title: str
    description: str
    poster_url: str | None = None
    watched_at: datetime


class DashboardResponse(BaseModel):
    total_watch_time: TotalWatchTimeResponse
    movies_count: int
    series_count: int
    episodes_count: int
    average_rating: float | None = None
    last_watched: list[LastWatchedItem]
