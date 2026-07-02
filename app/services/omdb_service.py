from __future__ import annotations

from typing import Any

import httpx

from app.core.config import settings
from app.core.exceptions import (
    BadRequestException,
    NotFoundException,
    ProviderNotImplementedException,
    UpstreamServiceException,
)
from app.models.title import TitleType
from app.schemas.omdb import OmdbEpisodeItem, OmdbSeasonEpisodes, OmdbTitleDetails, OmdbTitleSearchItem

MOCK_TITLES: list[OmdbTitleDetails] = [
    OmdbTitleDetails(
        imdb_id="tt0903747",
        title="Breaking Bad",
        original_title="Breaking Bad",
        title_type=TitleType.series,
        year=2008,
        poster_url="https://m.media-amazon.com/images/M/MV5B_breaking_bad.jpg",
        plot=(
            "A chemistry teacher diagnosed with inoperable lung cancer turns to "
            "manufacturing and selling methamphetamine."
        ),
        runtime_minutes=None,
        total_seasons=5,
    ),
    OmdbTitleDetails(
        imdb_id="tt0816692",
        title="Interstellar",
        original_title="Interstellar",
        title_type=TitleType.movie,
        year=2014,
        poster_url="https://m.media-amazon.com/images/M/MV5B_interstellar.jpg",
        plot=(
            "A team of explorers travel through a wormhole in space in an attempt "
            "to ensure humanity's survival."
        ),
        runtime_minutes=169,
        total_seasons=None,
    ),
]

MOCK_EPISODES: dict[str, list[OmdbSeasonEpisodes]] = {
    "tt0903747": [
        OmdbSeasonEpisodes(
            season_number=1,
            episodes=[
                OmdbEpisodeItem(
                    imdb_episode_id="tt0959621",
                    season_number=1,
                    episode_number=1,
                    title="Pilot",
                    plot="Walter White begins his transformation.",
                    runtime_minutes=58,
                ),
                OmdbEpisodeItem(
                    imdb_episode_id="tt1054724",
                    season_number=1,
                    episode_number=2,
                    title="Cat's in the Bag...",
                    plot="Walt and Jesse try to deal with the consequences.",
                    runtime_minutes=48,
                ),
            ],
        )
    ]
}


class OmdbService:
    async def search_titles(self, query: str) -> list[OmdbTitleSearchItem]:
        if settings.OMDB_PROVIDER_MODE == "mock":
            term = query.casefold().strip()
            return [
                title
                for title in MOCK_TITLES
                if term in title.title.casefold() or term in (title.original_title or "").casefold()
            ]

        data = await self._request({"s": query.strip()})
        results = data.get("Search", [])

        return [
            self._map_search_item(item)
            for item in results
            if self._coerce_title_type(item.get("Type")) is not None
        ]

    async def get_title_details(self, imdb_id: str) -> OmdbTitleDetails:
        if settings.OMDB_PROVIDER_MODE == "mock":
            for title in MOCK_TITLES:
                if title.imdb_id == imdb_id:
                    return title
            raise NotFoundException("OMDb title not found.")

        data = await self._request({"i": imdb_id, "plot": "full"})
        return self._map_title_details(data)

    async def get_series_episodes(self, imdb_id: str) -> list[OmdbSeasonEpisodes]:
        if settings.OMDB_PROVIDER_MODE == "mock":
            title = next((title for title in MOCK_TITLES if title.imdb_id == imdb_id), None)
            if title and title.title_type != TitleType.series:
                raise NotFoundException("Episodes are only available for series.")
            episodes = MOCK_EPISODES.get(imdb_id)
            if not episodes:
                raise NotFoundException("OMDb series episodes not found.")
            return episodes

        details = await self.get_title_details(imdb_id)
        if details.title_type != TitleType.series:
            raise BadRequestException("Episodes are only available for series.")
        if not details.total_seasons or details.total_seasons < 1:
            return []

        seasons: list[OmdbSeasonEpisodes] = []
        for season_number in range(1, details.total_seasons + 1):
            season_data = await self._request({"i": imdb_id, "Season": season_number})
            raw_episodes = season_data.get("Episodes", [])

            seasons.append(
                OmdbSeasonEpisodes(
                    season_number=season_number,
                    episodes=[
                        OmdbEpisodeItem(
                            imdb_episode_id=episode.get("imdbID", ""),
                            season_number=season_number,
                            episode_number=self._parse_int(episode.get("Episode")),
                            title=episode.get("Title", "Unknown"),
                            plot=None,
                            runtime_minutes=None,
                        )
                        for episode in raw_episodes
                        if episode.get("imdbID")
                    ],
                )
            )

        return seasons

    async def _request(self, params: dict[str, Any]) -> dict[str, Any]:
        if not settings.OMDB_API_KEY:
            raise ProviderNotImplementedException("Set OMDB_API_KEY in the .env file to use OMDb.")

        request_params = {
            "apikey": settings.OMDB_API_KEY,
            "r": "json",
            **params,
        }

        try:
            async with httpx.AsyncClient(base_url=settings.OMDB_API_BASE_URL, timeout=20.0) as client:
                response = await client.get("/", params=request_params)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as exc:
            raise UpstreamServiceException("Unable to reach OMDb at the moment.") from exc
        except ValueError as exc:
            raise UpstreamServiceException("OMDb returned an invalid response.") from exc

        if data.get("Response") == "False":
            error_message = data.get("Error", "OMDb request failed.")
            lowered = error_message.lower()

            if "not found" in lowered:
                raise NotFoundException(error_message)
            raise BadRequestException(error_message)

        return data

    def _map_search_item(self, item: dict[str, Any]) -> OmdbTitleSearchItem:
        title_type = self._coerce_title_type(item.get("Type"))
        if title_type is None:
            raise BadRequestException("OMDb returned an unsupported title type.")
        return OmdbTitleSearchItem(
            imdb_id=item.get("imdbID", ""),
            title=item.get("Title", "Unknown"),
            original_title=item.get("Title"),
            title_type=title_type,
            year=self._extract_year(item.get("Year")),
            poster_url=self._normalize_poster(item.get("Poster")),
            plot=None,
            runtime_minutes=None,
        )

    def _map_title_details(self, item: dict[str, Any]) -> OmdbTitleDetails:
        title_type = self._coerce_title_type(item.get("Type"))
        if title_type is None:
            raise BadRequestException("Only movie and series titles are supported.")
        return OmdbTitleDetails(
            imdb_id=item.get("imdbID", ""),
            title=item.get("Title", "Unknown"),
            original_title=item.get("Title"),
            title_type=title_type,
            year=self._extract_year(item.get("Year")),
            poster_url=self._normalize_poster(item.get("Poster")),
            plot=self._none_if_na(item.get("Plot")),
            runtime_minutes=self._parse_runtime_minutes(item.get("Runtime")),
            total_seasons=self._parse_int(item.get("totalSeasons")),
        )

    def _coerce_title_type(self, value: Any) -> TitleType | None:
        if value == "series":
            return TitleType.series
        if value == "movie":
            return TitleType.movie
        return None

    def _extract_year(self, value: Any) -> int | None:
        text = str(value or "").strip()
        if not text or text == "N/A":
            return None
        first_part = text.split("–")[0].split("-")[0].strip()
        return self._parse_int(first_part)

    def _parse_runtime_minutes(self, value: Any) -> int | None:
        text = str(value or "").strip()
        if not text or text == "N/A":
            return None
        first_part = text.split(" ")[0]
        return self._parse_int(first_part)

    def _parse_int(self, value: Any) -> int | None:
        try:
            return int(str(value).strip())
        except (TypeError, ValueError):
            return None

    def _normalize_poster(self, value: Any) -> str | None:
        text = str(value or "").strip()
        if not text or text == "N/A":
            return None
        return text

    def _none_if_na(self, value: Any) -> str | None:
        text = str(value or "").strip()
        if not text or text == "N/A":
            return None
        return text
