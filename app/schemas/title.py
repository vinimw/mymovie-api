from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.title import TitleType, WatchStatus


class WatchedEpisodeCreate(BaseModel):
    imdb_episode_id: str
    season_number: int = Field(ge=1)
    episode_number: int = Field(ge=1)
    title: str
    plot: str | None = None
    runtime_minutes: int | None = Field(default=None, ge=1)
    watched_at: datetime | None = None


class WatchedEpisodeBulkCreate(BaseModel):
    episodes: list[WatchedEpisodeCreate] = Field(default_factory=list)


class WatchedEpisodeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    watched_title_id: int
    imdb_episode_id: str
    season_number: int
    episode_number: int
    title: str
    plot: str | None = None
    runtime_minutes: int | None = None
    watched_at: datetime
    created_at: datetime


class WatchedTitleCreate(BaseModel):
    imdb_id: str
    title: str
    original_title: str | None = None
    title_type: TitleType
    year: int | None = None
    poster_url: str | None = None
    plot: str | None = None
    comments: str | None = Field(default=None, max_length=2000)
    runtime_minutes: int | None = Field(default=None, ge=1)
    user_rating: int | None = Field(default=None, ge=1, le=5)
    status: WatchStatus
    watched_at: datetime | None = None
    episodes: list[WatchedEpisodeCreate] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_payload(self) -> "WatchedTitleCreate":
        if self.title_type == TitleType.movie and self.episodes:
            raise ValueError("Movies cannot receive episodes.")
        return self

    @field_validator("comments")
    @classmethod
    def normalize_comments(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class WatchedTitleUpdate(BaseModel):
    user_rating: int | None = Field(default=None, ge=1, le=5)
    status: WatchStatus | None = None
    comments: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def ensure_any_value(self) -> "WatchedTitleUpdate":
        if (
            self.user_rating is None
            and self.status is None
            and "comments" not in self.model_fields_set
        ):
            raise ValueError("Provide at least one field to update.")
        return self

    @field_validator("comments")
    @classmethod
    def normalize_comments(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class WatchedTitleListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    imdb_id: str
    title: str
    original_title: str | None = None
    title_type: TitleType
    year: int | None = None
    poster_url: str | None = None
    plot: str | None = None
    comments: str | None = None
    runtime_minutes: int | None = None
    user_rating: int | None = None
    status: WatchStatus
    watched_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    episodes: list[WatchedEpisodeResponse] = Field(default_factory=list)


class WatchedTitleResponse(WatchedTitleListItem):
    pass
