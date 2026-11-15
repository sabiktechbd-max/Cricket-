# Cricbuzz API

An unofficial REST API that scrapes and structures live cricket data from
[cricbuzz.com](https://www.cricbuzz.com/): matches, scorecards, commentary,
squads, series, rankings, news, videos, photos, teams and players.

The service is built with FastAPI and has no third-party scraping dependencies
beyond the web framework itself.

## How it works

Cricbuzz is a Next.js App Router site. Every page embeds its server-side props
as a React Server Components (RSC) "flight" stream, delivered as a series of
`self.__next_f.push([1, "<json-string>"])` calls inside the HTML. The scraper
reassembles and unescapes that stream and then walks the resulting object graph
for the keys it needs (for example `matchHeader`, `scoreCard`,
`matchPreviewFullComm`, `pointsTable`, `newsCardsData`). No headless browser is
required.

Key modules:

| File | Responsibility |
| --- | --- |
| `cricbuzz_api/client.py` | HTTP fetching, RSC flight-stream parsing, TTL cache |
| `cricbuzz_api/scraper.py` | Per-section extractors returning clean JSON |
| `cricbuzz_api/main.py` | FastAPI application and routes |

## Install

```bash
pip install -r requirements.txt
```

## Run

```bash
uvicorn cricbuzz_api.main:app --host 0.0.0.0 --port 8000
```

or:

```bash
python -m cricbuzz_api.server
```

Interactive OpenAPI docs are at <http://localhost:8000/docs>.

## Endpoints

### Matches

| Method | Path | Description |
| --- | --- | --- |
| GET | `/matches/live` | Currently live matches |
| GET | `/matches` | Matches grouped by type (International, League, Domestic, Women) |
| GET | `/matches/upcoming` | Upcoming fixtures |
| GET | `/matches/recent` | Recently completed matches |
| GET | `/matches/{match_id}/info` | Match header and mini-score |
| GET | `/matches/{match_id}/scorecard` | Full scorecard |
| GET | `/matches/{match_id}/commentary` | Ball-by-ball commentary |
| GET | `/matches/{match_id}/overs` | Over-by-over summary |
| GET | `/matches/{match_id}/squads` | Playing XI and squads |
| GET | `/matches/{match_id}/highlights` | Commentary highlights |
| GET | `/matches/{match_id}/news` | News linked to the match |
| GET | `/matches/{match_id}/forecast` | Win probability and prediction |

### Series

| Method | Path | Description |
| --- | --- | --- |
| GET | `/series` | Series list |
| GET | `/series/{series_id}` | Series home (matches, news, squads) |
| GET | `/series/{series_id}/matches` | All matches in the series |
| GET | `/series/{series_id}/points-table` | Points table |
| GET | `/series/{series_id}/stats` | Series statistics |
| GET | `/series/{series_id}/squads` | Series squads |
| GET | `/series/{series_id}/venues` | Venues |
| GET | `/series/{series_id}/news` | Series news |
| GET | `/series/{series_id}/videos` | Series videos |
| GET | `/series/{series_id}/photos` | Series photo galleries |

### Teams, players, rankings

| Method | Path | Description |
| --- | --- | --- |
| GET | `/teams` | Team list |
| GET | `/teams/{team_id}` | Team profile and schedule |
| GET | `/teams/{team_id}/schedule` | Team schedule |
| GET | `/teams/{team_id}/results` | Team results |
| GET | `/teams/{team_id}/stats` | Team statistics |
| GET | `/players/{player_id}` | Player profile |
| GET | `/rankings/{gender}/{category}` | ICC rankings (`gender`: `men`/`women`; `category`: `batting`/`bowling`/`all-rounder`/`teams`) |

### News, videos, photos, schedule

| Method | Path | Description |
| --- | --- | --- |
| GET | `/news` | Latest news |
| GET | `/news/{story_id}` | News article |
| GET | `/videos` | Latest videos |
| GET | `/videos/{video_id}` | Video detail |
| GET | `/photos` | Photo galleries |
| GET | `/photos/{gallery_id}` | Gallery images |
| GET | `/schedule` | Upcoming schedule (`?scope=all\|international\|league\|domestic\|women`) |
| GET | `/archives` | Historical series archive |
| GET | `/search` | Search teams, live matches, series and news (`?q=india`) |

### Meta

`GET /` lists all routes and `GET /health` is a liveness probe.

## Notes on slugs

Cricbuzz URLs contain a descriptive slug that the server ignores, for example
`/cricket-series/12543/india-tour-of-new-zealand-2026/matches`. Every endpoint
that maps to such a URL accepts an optional `slug` query parameter. If you omit
it, a placeholder is used and the request still resolves, because only the
numeric id matters:

```
/series/12543/matches?slug=india-tour-of-new-zealand-2026
/series/12543/matches          # also works
```

## Tests

Network-free unit tests:

```bash
pytest
```

Live integration tests that hit cricbuzz.com:

```bash
CRICBUZZ_LIVE_TESTS=1 pytest
```

## Disclaimer

This project is not affiliated with Cricbuzz. It reads publicly served pages;
respect Cricbuzz's terms of service and keep request rates modest. Responses
are cached for 30 seconds by default to reduce load.
