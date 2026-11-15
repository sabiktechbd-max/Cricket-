"""End-to-end tests for the FastAPI app.

These hit the live cricbuzz.com site through the server, so they are opt-in:
run with ``CRICBUZZ_LIVE_TESTS=1 pytest``.
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from cricbuzz_api.main import app

pytestmark = pytest.mark.skipif(
    os.environ.get("CRICBUZZ_LIVE_TESTS") != "1",
    reason="set CRICBUZZ_LIVE_TESTS=1 to run live integration tests",
)

client = TestClient(app)


def test_root_lists_endpoints():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "/matches/live" in resp.json()["endpoints"]


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


@pytest.mark.parametrize(
    "path",
    [
        "/matches/live",
        "/matches",
        "/matches/upcoming",
        "/series",
        "/teams",
        "/news",
        "/videos",
        "/photos",
        "/schedule",
        "/archives",
        "/rankings/men/batting",
    ],
)
def test_list_endpoints_return_200(path):
    resp = client.get(path)
    assert resp.status_code == 200


def test_match_subresources():
    for section in ["info", "scorecard", "commentary", "overs", "squads", "highlights"]:
        resp = client.get(f"/matches/161282/{section}")
        assert resp.status_code == 200, section
        assert resp.json()
