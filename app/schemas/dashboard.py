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
    owner_display_names: list[str] = []
    watched_at: datetime


class DashboardSummary(BaseModel):
    email: str
    display_name: str
    total_watch_time: TotalWatchTimeResponse
    movies_count: int
    series_count: int
    episodes_count: int
    average_rating: float | None = None


class DashboardResponse(BaseModel):
    current_user: DashboardSummary
    other_users: list[DashboardSummary]
    last_watched: list[LastWatchedItem]
