"""FastAPI application exposing Cricbuzz data as a REST API.

Run with::

    uvicorn cricbuzz_api.main:app --reload

Interactive docs are available at ``/docs``.
"""

from __future__ import annotations

from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .client import CricbuzzClient, CricbuzzError
from . import scraper

_client = CricbuzzClient(ttl=30.0)


app = FastAPI(
    title="Cricbuzz API",
    description=(
        "Unofficial REST API that scrapes and structures live cricket data from "
        "cricbuzz.com: matches, scorecards, commentary, squads, series, rankings, "
        "news, videos, photos, teams and players."
    ),
    version=__version__,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_client() -> CricbuzzClient:
    return _client


def _handle(func, *args, **kwargs) -> Any:
    try:
        return func(*args, **kwargs)
    except CricbuzzError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/", tags=["meta"])
def root() -> dict[str, Any]:
    return {
        "name": "Cricbuzz API",
        "version": __version__,
        "source": "https://www.cricbuzz.com/",
        "docs": "/docs",
        "endpoints": [r.path for r in app.routes if getattr(r, "methods", None)],
    }


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok"}


# --------------------------------------------------------------------------- #
# Matches
# --------------------------------------------------------------------------- #
@app.get("/matches/live", tags=["matches"])
def matches_live(client: CricbuzzClient = Depends(get_client)) -> Any:
    return _handle(scraper.live_matches, client)


@app.get("/matches", tags=["matches"])
def matches_by_type(client: CricbuzzClient = Depends(get_client)) -> Any:
    return _handle(scraper.matches_by_type, client)


@app.get("/matches/upcoming", tags=["matches"])
def matches_upcoming(client: CricbuzzClient = Depends(get_client)) -> Any:
    return _handle(scraper.upcoming_matches, client)


@app.get("/matches/recent", tags=["matches"])
def matches_recent(client: CricbuzzClient = Depends(get_client)) -> Any:
    return _handle(scraper.recent_matches, client)


@app.get("/matches/{match_id}/info", tags=["matches"])
def match_info(match_id: str, client: CricbuzzClient = Depends(get_client)) -> Any:
    return _handle(scraper.match_info, client, match_id)


@app.get("/matches/{match_id}/scorecard", tags=["matches"])
def match_scorecard(match_id: str, client: CricbuzzClient = Depends(get_client)) -> Any:
    return _handle(scraper.match_scorecard, client, match_id)


@app.get("/matches/{match_id}/commentary", tags=["matches"])
def match_commentary(match_id: str, client: CricbuzzClient = Depends(get_client)) -> Any:
    return _handle(scraper.match_commentary, client, match_id)


@app.get("/matches/{match_id}/overs", tags=["matches"])
def match_overs(match_id: str, client: CricbuzzClient = Depends(get_client)) -> Any:
    return _handle(scraper.match_overs, client, match_id)


@app.get("/matches/{match_id}/squads", tags=["matches"])
def match_squads(match_id: str, client: CricbuzzClient = Depends(get_client)) -> Any:
    return _handle(scraper.match_squads, client, match_id)


@app.get("/matches/{match_id}/highlights", tags=["matches"])
def match_highlights(match_id: str, client: CricbuzzClient = Depends(get_client)) -> Any:
    return _handle(scraper.match_highlights, client, match_id)


@app.get("/matches/{match_id}/news", tags=["matches"])
def match_news(match_id: str, client: CricbuzzClient = Depends(get_client)) -> Any:
    return _handle(scraper.match_news, client, match_id)


@app.get("/matches/{match_id}/forecast", tags=["matches"])
def match_forecast(match_id: str, client: CricbuzzClient = Depends(get_client)) -> Any:
    return _handle(scraper.match_forecast, client, match_id)


# --------------------------------------------------------------------------- #
# Series
# --------------------------------------------------------------------------- #
@app.get("/series", tags=["series"])
def series_list(client: CricbuzzClient = Depends(get_client)) -> Any:
    return _handle(scraper.series_list, client)


@app.get("/series/{series_id}", tags=["series"])
def series_detail(
    series_id: str,
    slug: str | None = Query(None, description="Optional URL slug, ignored by Cricbuzz"),
    client: CricbuzzClient = Depends(get_client),
) -> Any:
    return _handle(scraper.series_detail, client, series_id, slug)


@app.get("/series/{series_id}/matches", tags=["series"])
def series_matches(
    series_id: str, slug: str | None = Query(None), client: CricbuzzClient = Depends(get_client)
) -> Any:
    return _handle(scraper.series_matches, client, series_id, slug)


@app.get("/series/{series_id}/points-table", tags=["series"])
def series_points_table(
    series_id: str, slug: str | None = Query(None), client: CricbuzzClient = Depends(get_client)
) -> Any:
    return _handle(scraper.series_points_table, client, series_id, slug)


@app.get("/series/{series_id}/stats", tags=["series"])
def series_stats(
    series_id: str, slug: str | None = Query(None), client: CricbuzzClient = Depends(get_client)
) -> Any:
    return _handle(scraper.series_stats, client, series_id, slug)


@app.get("/series/{series_id}/squads", tags=["series"])
def series_squads(
    series_id: str, slug: str | None = Query(None), client: CricbuzzClient = Depends(get_client)
) -> Any:
    return _handle(scraper.series_squads, client, series_id, slug)


@app.get("/series/{series_id}/venues", tags=["series"])
def series_venues(
    series_id: str, slug: str | None = Query(None), client: CricbuzzClient = Depends(get_client)
) -> Any:
    return _handle(scraper.series_venues, client, series_id, slug)


@app.get("/series/{series_id}/news", tags=["series"])
def series_news(
    series_id: str, slug: str | None = Query(None), client: CricbuzzClient = Depends(get_client)
) -> Any:
    return _handle(scraper.series_news, client, series_id, slug)


@app.get("/series/{series_id}/videos", tags=["series"])
def series_videos(
    series_id: str, slug: str | None = Query(None), client: CricbuzzClient = Depends(get_client)
) -> Any:
    return _handle(scraper.series_videos, client, series_id, slug)


@app.get("/series/{series_id}/photos", tags=["series"])
def series_photos(
    series_id: str, slug: str | None = Query(None), client: CricbuzzClient = Depends(get_client)
) -> Any:
    return _handle(scraper.series_photos, client, series_id, slug)


# --------------------------------------------------------------------------- #
# Teams & players
# --------------------------------------------------------------------------- #
@app.get("/teams", tags=["teams"])
def teams(client: CricbuzzClient = Depends(get_client)) -> Any:
    return _handle(scraper.team_list, client)


@app.get("/teams/{team_id}", tags=["teams"])
def team_detail(
    team_id: str, slug: str | None = Query(None), client: CricbuzzClient = Depends(get_client)
) -> Any:
    return _handle(scraper.team_detail, client, team_id, slug)


@app.get("/teams/{team_id}/schedule", tags=["teams"])
def team_schedule(
    team_id: str, slug: str | None = Query(None), client: CricbuzzClient = Depends(get_client)
) -> Any:
    return _handle(scraper.team_schedule, client, team_id, slug)


@app.get("/teams/{team_id}/results", tags=["teams"])
def team_results(
    team_id: str, slug: str | None = Query(None), client: CricbuzzClient = Depends(get_client)
) -> Any:
    return _handle(scraper.team_results, client, team_id, slug)


@app.get("/teams/{team_id}/stats", tags=["teams"])
def team_stats(
    team_id: str, slug: str | None = Query(None), client: CricbuzzClient = Depends(get_client)
) -> Any:
    return _handle(scraper.team_stats, client, team_id, slug)


@app.get("/players/{player_id}", tags=["players"])
def player_profile(
    player_id: str, slug: str | None = Query(None), client: CricbuzzClient = Depends(get_client)
) -> Any:
    return _handle(scraper.player_profile, client, player_id, slug)


# --------------------------------------------------------------------------- #
# Rankings
# --------------------------------------------------------------------------- #
@app.get("/rankings/{gender}/{category}", tags=["rankings"])
def rankings(gender: str, category: str, client: CricbuzzClient = Depends(get_client)) -> Any:
    return _handle(scraper.rankings, client, category, gender)


# --------------------------------------------------------------------------- #
# News, videos, photos
# --------------------------------------------------------------------------- #
@app.get("/news", tags=["news"])
def news_list(client: CricbuzzClient = Depends(get_client)) -> Any:
    return _handle(scraper.news_list, client)


@app.get("/news/{story_id}", tags=["news"])
def news_detail(
    story_id: str, slug: str | None = Query(None), client: CricbuzzClient = Depends(get_client)
) -> Any:
    return _handle(scraper.news_detail, client, story_id, slug)


@app.get("/videos", tags=["videos"])
def videos(client: CricbuzzClient = Depends(get_client)) -> Any:
    return _handle(scraper.videos_list, client)


@app.get("/videos/{video_id}", tags=["videos"])
def video_detail(
    video_id: str, slug: str | None = Query(None), client: CricbuzzClient = Depends(get_client)
) -> Any:
    return _handle(scraper.video_detail, client, video_id, slug)


@app.get("/photos", tags=["photos"])
def photos(client: CricbuzzClient = Depends(get_client)) -> Any:
    return _handle(scraper.photo_galleries, client)


@app.get("/photos/{gallery_id}", tags=["photos"])
def gallery_detail(
    gallery_id: str, slug: str | None = Query(None), client: CricbuzzClient = Depends(get_client)
) -> Any:
    return _handle(scraper.gallery_detail, client, gallery_id, slug)


# --------------------------------------------------------------------------- #
# Search & archives
# --------------------------------------------------------------------------- #
@app.get("/search", tags=["search"])
def search(
    q: str = Query(..., min_length=1, description="Free-text query"),
    client: CricbuzzClient = Depends(get_client),
) -> Any:
    return _handle(scraper.search, client, q)


@app.get("/schedule", tags=["schedule"])
def schedule(
    scope: str = Query("all", description="all | international | league | domestic | women"),
    client: CricbuzzClient = Depends(get_client),
) -> Any:
    return _handle(scraper.schedule, client, scope)


@app.get("/archives", tags=["schedule"])
def archives(client: CricbuzzClient = Depends(get_client)) -> Any:
    return _handle(scraper.archives, client)
