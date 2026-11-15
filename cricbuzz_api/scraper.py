"""High-level cricbuzz scrapers.

Each function maps one Cricbuzz section to a clean, JSON-serialisable
structure. All of them take a :class:`~cricbuzz_api.client.CricbuzzClient`
so HTTP fetching and caching stay centralised.
"""

from __future__ import annotations

import json
from typing import Any

from .client import CricbuzzClient, CricbuzzError, walk

IMAGE_BASE = "https://static.cricbuzz.com/a/img/v1/i1/c{image_id}/i.jpg"
FACE_IMAGE_BASE = "http://i.cricketcb.com/stats/img/faceImages/{player_id}.jpg"
RANK_IMAGE_BASE = "https://static.cricbuzz.com/a/img/v1/0x0/i1/c{image_id}/i.jpg"


def _series_path(series_id: int | str, slug: str | None = None) -> str:
    slug = slug or "series"
    return f"/cricket-series/{series_id}/{slug}"


def _team_path(team_id: int | str, slug: str | None = None) -> str:
    # Cricbuzz requires the ``{slug}/{id}`` form; the slug value is ignored.
    return f"/cricket-team/{slug or 'team'}/{team_id}"


def _match_path(match_id: int | str, section: str, slug: str | None = None) -> str:
    base = {
        "info": "/live-cricket-scores",
        "scorecard": "/live-cricket-scorecard",
        "commentary": "/live-cricket-full-commentary",
        "overs": "/live-cricket-over-by-over",
        "squads": "/cricket-match-squads",
        "highlights": "/cricket-match-highlights",
        "news": "/cricket-match-news",
        "forecast": "/cricket-match-forecast",
    }[section]
    if slug:
        return f"{base}/{match_id}/{slug}"
    return f"{base}/{match_id}"


# --------------------------------------------------------------------------- #
# Matches
# --------------------------------------------------------------------------- #
def _match_card(match: dict[str, Any]) -> dict[str, Any]:
    """Normalise a match entry from ``matchesList`` / ``currentMatchesList``."""
    info = match.get("matchInfo", match)
    return {
        "matchId": info.get("matchId"),
        "seriesId": info.get("seriesId"),
        "seriesName": info.get("seriesName"),
        "matchDesc": info.get("matchDesc"),
        "matchFormat": info.get("matchFormat"),
        "startDate": info.get("startDate"),
        "endDate": info.get("endDate"),
        "state": info.get("state"),
        "status": info.get("status"),
        "team1": info.get("team1"),
        "team2": info.get("team2"),
        "venueInfo": info.get("venueInfo"),
        "seriesStartDt": info.get("seriesStartDt"),
        "seriesEndDt": info.get("seriesEndDt"),
        "isLiveStreamEnabled": info.get("isLiveStreamEnabled"),
        "matchScore": match.get("matchScore"),
    }


def live_matches(client: CricbuzzClient) -> list[dict[str, Any]]:
    data = client.extract("/cricket-match/live-scores", "matchesList")
    return [_match_card(m["match"]) for m in data.get("matches", [])]


def matches_by_type(client: CricbuzzClient, path: str = "/cricket-match/live-scores") -> list[dict[str, Any]]:
    """Matches grouped by type (International, League, Domestic, Women)."""
    data = client.extract(path, "currentMatchesList")
    groups = []
    for type_match in data.get("typeMatches", []):
        series = []
        for series_match in type_match.get("seriesMatches", []):
            wrapper = series_match.get("seriesAdWrapper", {})
            series.append(
                {
                    "seriesId": wrapper.get("seriesId"),
                    "seriesName": wrapper.get("seriesName"),
                    "matches": [_match_card(m) for m in wrapper.get("matches", [])],
                }
            )
        groups.append({"matchType": type_match.get("matchType"), "seriesMatches": series})
    return groups


def _matches_from_schedule(schedule: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for day in schedule:
        wrapper = day.get("scheduleAdWrapper", {})
        for series in wrapper.get("matchScheduleList", []):
            for match in series.get("matchInfo", []):
                out.append(
                    {
                        "date": wrapper.get("date"),
                        "seriesId": series.get("seriesId"),
                        "seriesName": series.get("seriesName"),
                        "matchId": match.get("matchId"),
                        "matchDesc": match.get("matchDesc"),
                        "matchFormat": match.get("matchFormat"),
                        "startDate": match.get("startDate"),
                        "endDate": match.get("endDate"),
                        "state": match.get("state"),
                        "status": match.get("status"),
                        "team1": match.get("team1"),
                        "team2": match.get("team2"),
                        "venueInfo": match.get("venueInfo"),
                    }
                )
    return out


def upcoming_matches(client: CricbuzzClient) -> list[dict[str, Any]]:
    data = client.extract("/cricket-schedule/upcoming-series/all", "matchScheduleMap")
    return _matches_from_schedule(data)


def recent_matches(client: CricbuzzClient) -> list[dict[str, Any]]:
    """Recent results: schedule matches that are no longer upcoming."""
    data = client.extract("/cricket-match/live-scores/recent", "currentMatchesList")
    groups = []
    for type_match in data.get("typeMatches", []):
        for series_match in type_match.get("seriesMatches", []):
            wrapper = series_match.get("seriesAdWrapper", {})
            for match in wrapper.get("matches", []):
                groups.append(_match_card(match))
    return groups


def match_info(client: CricbuzzClient, match_id: int | str) -> dict[str, Any]:
    path = _match_path(match_id, "info")
    header = client.extract(path, "matchHeader")
    result: dict[str, Any] = {"matchHeader": header}
    miniscore = client.extract(path, "miniscore", required=False)
    if miniscore:
        result["miniscore"] = miniscore
    return result


def match_scorecard(client: CricbuzzClient, match_id: int | str) -> dict[str, Any]:
    path = _match_path(match_id, "scorecard")
    return {
        "matchHeader": client.extract(path, "matchHeader", required=False),
        "scoreCard": client.extract(path, "scoreCard", required=False),
    }


def match_commentary(client: CricbuzzClient, match_id: int | str) -> dict[str, Any]:
    path = _match_path(match_id, "commentary")
    data = client.extract(path, "matchPreviewFullComm", required=False) or {}
    return {
        "matchHeader": (data.get("matchDetails") or {}).get("matchHeader"),
        "commentary": data.get("commentary"),
    }


def match_overs(client: CricbuzzClient, match_id: int | str) -> dict[str, Any]:
    path = _match_path(match_id, "overs")
    return {
        "matchHeader": client.extract(path, "matchHeader", required=False),
        "overSummaryList": client.extract(path, "overSummaryList", required=False),
    }


def match_squads(client: CricbuzzClient, match_id: int | str) -> dict[str, Any]:
    path = _match_path(match_id, "squads")
    return {
        "matchHeader": client.extract(path, "matchHeader", required=False),
        "squads": client.extract(path, "squads", required=False)
        or client.extract(path, "players", required=False),
    }


def match_highlights(client: CricbuzzClient, match_id: int | str) -> dict[str, Any]:
    path = _match_path(match_id, "highlights")
    return {
        "matchHeader": client.extract(path, "matchHeader", required=False),
        "commentaryList": client.extract(path, "commentaryList", required=False),
    }


def match_news(client: CricbuzzClient, match_id: int | str) -> dict[str, Any]:
    path = _match_path(match_id, "news")
    data = client.extract(path, "newsCardsData", required=False) or []
    return {
        "matchHeader": client.extract(path, "matchHeader", required=False),
        "newsList": [
            {
                "storyId": item.get("id"),
                "headline": item.get("headline"),
                "intro": item.get("intro"),
                "publishedTime": item.get("publishedTime"),
                "storyType": item.get("storyType"),
                "imageId": (item.get("imageDetails") or {}).get("imageId"),
                "url": f"/cricket-news/{item.get('id')}",
            }
            for item in data
        ],
    }


def match_forecast(client: CricbuzzClient, match_id: int | str) -> dict[str, Any]:
    path = _match_path(match_id, "forecast")
    return {
        "matchHeader": client.extract(path, "matchHeader", required=False),
        "winProbability": client.extract(path, "winProbability", required=False),
        "prediction": client.extract(path, "cbPrediction", required=False),
    }


# --------------------------------------------------------------------------- #
# Series
# --------------------------------------------------------------------------- #
def _matches_from_match_details_map(data: Any) -> list[dict[str, Any]]:
    """Flatten a ``matchDetailsMap`` (dict keyed by date) or list of them."""
    out: list[dict[str, Any]] = []
    blocks = data if isinstance(data, list) else [data]
    for block in blocks:
        if not isinstance(block, dict):
            continue
        details = block.get("matchDetailsMap", block)
        for match in details.get("match", []):
            card = _match_card(match)
            card["date"] = details.get("key")
            out.append(card)
    return out


def series_matches(client: CricbuzzClient, series_id: int | str, slug: str | None = None) -> dict[str, Any]:
    path = f"{_series_path(series_id, slug)}/matches"
    data = client.extract(path, "matchDetailsMap")
    return {"seriesId": series_id, "matches": _matches_from_match_details_map(data)}


def series_points_table(client: CricbuzzClient, series_id: int | str, slug: str | None = None) -> dict[str, Any]:
    path = f"{_series_path(series_id, slug)}/points-table"
    table = client.extract(path, "pointsTable", required=False)
    return {"seriesId": series_id, "pointsTable": table}


def series_stats(client: CricbuzzClient, series_id: int | str, slug: str | None = None) -> dict[str, Any]:
    path = f"{_series_path(series_id, slug)}/stats"
    stats = client.extract(path, "initialStats", required=False)
    return {"seriesId": series_id, "stats": stats}


def series_squads(client: CricbuzzClient, series_id: int | str, slug: str | None = None) -> dict[str, Any]:
    path = f"{_series_path(series_id, slug)}/squads"
    squads = client.extract(path, "squads", required=False)
    return {"seriesId": series_id, "squads": squads}


def series_venues(client: CricbuzzClient, series_id: int | str, slug: str | None = None) -> dict[str, Any]:
    path = f"{_series_path(series_id, slug)}/venues"
    venues = client.extract(path, "venueData", required=False)
    return {"seriesId": series_id, "venues": venues}


def series_news(client: CricbuzzClient, series_id: int | str, slug: str | None = None) -> dict[str, Any]:
    path = f"{_series_path(series_id, slug)}/news"
    return {"seriesId": series_id, "news": client.extract(path, "storyList", required=False)}


def series_videos(client: CricbuzzClient, series_id: int | str, slug: str | None = None) -> dict[str, Any]:
    path = f"{_series_path(series_id, slug)}/videos"
    data = client.extract(path, "videoData", required=False) or client.extract(path, "videoList", required=False)
    return {"seriesId": series_id, "videos": data}


def series_photos(client: CricbuzzClient, series_id: int | str, slug: str | None = None) -> dict[str, Any]:
    path = f"{_series_path(series_id, slug)}/photos"
    data = client.extract(path, "photosData", required=False)
    return {"seriesId": series_id, "photos": data}


def series_detail(client: CricbuzzClient, series_id: int | str, slug: str | None = None) -> dict[str, Any]:
    path = _series_path(series_id, slug)
    matches_path = f"{path}/matches"
    matches = []
    try:
        matches = _matches_from_match_details_map(client.extract(matches_path, "matchDetailsMap"))
    except CricbuzzError:
        pass
    return {
        "seriesId": series_id,
        "matches": matches,
        "news": client.extract(path, "storyList", required=False),
        "squads": client.extract(path, "squadsWidgetData", required=False),
    }


# --------------------------------------------------------------------------- #
# Teams & players
# --------------------------------------------------------------------------- #
def team_detail(client: CricbuzzClient, team_id: int | str, slug: str | None = None) -> dict[str, Any]:
    path = _team_path(team_id, slug)
    schedule: list[dict[str, Any]] = []
    try:
        data = client.extract(f"{path}/schedule", "teamMatchesData")
        schedule = _matches_from_match_details_map(data)
    except CricbuzzError:
        pass
    return {
        "teamId": team_id,
        "teamInfo": client.extract(path, "teamInfo", required=False),
        "schedule": schedule,
        "news": client.extract(path, "storyList", required=False),
    }


def team_schedule(client: CricbuzzClient, team_id: int | str, slug: str | None = None) -> dict[str, Any]:
    path = f"{_team_path(team_id, slug)}/schedule"
    data = client.extract(path, "teamMatchesData")
    return {"teamId": team_id, "schedule": _matches_from_match_details_map(data)}


def team_results(client: CricbuzzClient, team_id: int | str, slug: str | None = None) -> dict[str, Any]:
    path = f"{_team_path(team_id, slug)}/results"
    data = client.extract(path, "teamMatchesData")
    return {"teamId": team_id, "results": _matches_from_match_details_map(data)}


def team_stats(client: CricbuzzClient, team_id: int | str, slug: str | None = None) -> dict[str, Any]:
    path = f"{_team_path(team_id, slug)}/stats"
    return {"teamId": team_id, "stats": client.extract(path, "initialStats", required=False)}


def team_list(client: CricbuzzClient) -> list[dict[str, Any]]:
    data = client.extract("/cricket-team", "teamList")
    return [t for t in data if t.get("teamId")]


def player_profile(client: CricbuzzClient, player_id: int | str, slug: str | None = None) -> dict[str, Any]:
    path = f"/profiles/{player_id}/{slug or 'player'}"
    profile = client.extract(path, "playerData")
    return {
        "player": profile,
        "news": client.extract(path, "playerNews", required=False),
        "photo": FACE_IMAGE_BASE.format(player_id=profile.get("id", player_id)),
    }


# --------------------------------------------------------------------------- #
# Rankings
# --------------------------------------------------------------------------- #
def _clean(value: Any) -> Any:
    """Recursively replace RSC ``"$undefined"`` placeholders with ``None``."""
    if isinstance(value, dict):
        return {k: _clean(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_clean(v) for v in value]
    if value == "$undefined":
        return None
    return value


def rankings(client: CricbuzzClient, category: str = "batting", gender: str = "men") -> dict[str, Any]:
    path = f"/cricket-stats/icc-rankings/{gender}/{category}"
    data = client.extract(path, "data")
    return {
        "category": data.get("categoryType", category),
        "rankings": _clean(data.get("formatTypesData", {})),
    }


# --------------------------------------------------------------------------- #
# News, videos, photos
# --------------------------------------------------------------------------- #
def news_list(client: CricbuzzClient) -> list[dict[str, Any]]:
    data = client.extract("/cricket-news", "newsCardsData")
    return [
        {
            "storyId": item.get("id"),
            "headline": item.get("headline"),
            "intro": item.get("intro"),
            "publishedTime": item.get("publishedTime"),
            "storyType": item.get("storyType"),
            "context": item.get("context"),
            "imageId": (item.get("imageDetails") or {}).get("imageId"),
            "imageUrl": IMAGE_BASE.format(image_id=(item.get("imageDetails") or {}).get("imageId"))
            if (item.get("imageDetails") or {}).get("imageId")
            else None,
            "url": f"/cricket-news/{item.get('id')}",
        }
        for item in data
    ]


def news_detail(client: CricbuzzClient, story_id: int | str, slug: str | None = None) -> dict[str, Any]:
    path = f"/cricket-news/{story_id}/{slug or 'news'}"
    article = client.first_json_ld(path, "NewsArticle") or {}
    return {
        "storyId": story_id,
        "headline": article.get("headline") or article.get("name"),
        "description": article.get("description"),
        "body": article.get("articleBody"),
        "keywords": article.get("keywords"),
        "author": article.get("author"),
        "datePublished": article.get("datePublished"),
        "dateModified": article.get("dateModified"),
        "image": article.get("image"),
        "url": article.get("url"),
    }


def videos_list(client: CricbuzzClient) -> list[dict[str, Any]]:
    data = client.extract("/cricket-videos", "videoList")
    return [_video_card(item) for item in data]


def _video_card(item: dict[str, Any]) -> dict[str, Any]:
    video = item.get("video", item)
    return {
        "videoId": video.get("id"),
        "title": video.get("title"),
        "description": video.get("description"),
        "timestamp": video.get("timestamp"),
        "imageId": video.get("imageId"),
        "imageUrl": IMAGE_BASE.format(image_id=video.get("imageId")) if video.get("imageId") else None,
        "isLive": video.get("isLive"),
        "videoUrl": video.get("videoUrl"),
        "mappingId": video.get("mappingId"),
        "categories": video.get("categories") or video.get("category"),
    }


def video_detail(client: CricbuzzClient, video_id: int | str, slug: str | None = None) -> dict[str, Any]:
    path = f"/cricket-videos/{video_id}/{slug or 'video'}"
    data = client.extract(path, "data", required=False)
    if isinstance(data, dict):
        return _video_card(data)
    return {"videoId": video_id, "data": data}


def photo_galleries(client: CricbuzzClient) -> list[dict[str, Any]]:
    data = client.extract("/cricket-photo-gallery", "photosData")
    out = []
    for item in data:
        info = item.get("photoGalleryInfo", {})
        out.append(
            {
                "galleryId": info.get("galleryId"),
                "headline": info.get("headline"),
                "imageId": info.get("imageId"),
                "imageUrl": IMAGE_BASE.format(image_id=info.get("imageId")) if info.get("imageId") else None,
                "publishedTime": info.get("publishedTime"),
                "url": f"/cricket-gallery/{info.get('galleryId')}",
            }
        )
    return out


def gallery_detail(client: CricbuzzClient, gallery_id: int | str, slug: str | None = None) -> dict[str, Any]:
    path = f"/cricket-gallery/{gallery_id}/{slug or 'gallery'}"
    images = _gallery_images(client, path)
    return {"galleryId": gallery_id, "images": images}


def _gallery_images(client: CricbuzzClient, path: str) -> list[dict[str, Any]]:
    """Return the ImageObject JSON-LD entries from a gallery page."""
    images: list[dict[str, Any]] = []
    for block in client.json_ld(path):
        if block.get("@type") == "ImageObject":
            images.append(
                {
                    "headline": block.get("headline"),
                    "caption": block.get("caption"),
                    "image": block.get("image"),
                    "datePublished": block.get("datePublished"),
                }
            )
    return images


# --------------------------------------------------------------------------- #
# Search
# --------------------------------------------------------------------------- #
def search(client: CricbuzzClient, query: str) -> dict[str, Any]:
    """Case-insensitive search across teams, live matches, series and news.

    Cricbuzz's own search endpoint returns no data server-side, so this builds
    results from the publicly listed entities instead.
    """
    needle = query.strip().lower()
    if not needle:
        return {"query": query, "teams": [], "matches": [], "series": [], "news": []}

    teams = [t for t in team_list(client) if needle in json.dumps(t).lower()]

    matches = [m for m in live_matches(client) if needle in json.dumps(m).lower()]
    series = [s for s in series_list(client) if needle in json.dumps(s).lower()]
    news = [n for n in news_list(client) if needle in json.dumps(n).lower()]

    return {"query": query, "teams": teams, "matches": matches, "series": series, "news": news}


# --------------------------------------------------------------------------- #
# Schedule, series list, archives
# --------------------------------------------------------------------------- #
def schedule(client: CricbuzzClient, scope: str = "all") -> list[dict[str, Any]]:
    path = f"/cricket-schedule/upcoming-series/{scope}"
    data = client.extract(path, "matchScheduleMap")
    return _matches_from_schedule(data)


def series_list(client: CricbuzzClient) -> list[dict[str, Any]]:
    data = client.extract("/cricket-schedule/series/all", "seriesScheduleData")
    out = []
    for group in data:
        for series in group.get("series", []):
            out.append(
                {
                    "period": group.get("date"),
                    "seriesId": series.get("id"),
                    "name": series.get("name"),
                    "startDate": series.get("startDt"),
                    "endDate": series.get("endDt"),
                }
            )
    return out


def archives(client: CricbuzzClient) -> list[dict[str, Any]]:
    data = client.extract_all("/cricket-scorecard-archives", "seriesMapProto")
    out = []
    for block in data:
        for group in block:
            for series in group.get("series", []):
                out.append(
                    {
                        "year": group.get("date"),
                        "seriesId": series.get("id"),
                        "name": series.get("name"),
                        "startDate": series.get("startDt"),
                        "endDate": series.get("endDt"),
                    }
                )
    return out
