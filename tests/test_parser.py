"""Tests for the Cricbuzz RSC parser and scraper helpers.

Network-free tests run by default. Set ``CRICBUZZ_LIVE_TESTS=1`` to also run
the integration tests that hit cricbuzz.com.
"""

from __future__ import annotations

import os
import time

import pytest

from cricbuzz_api.client import CricbuzzClient, _TTLCache, flight_text, parse_rows, walk

SAMPLE_HTML = (
    "<script>self.__next_f.push([1,\"1a:[\\\"$\\\",\\\"div\\\",null,"
    "{\\\"matchHeader\\\":{\\\"matchId\\\":161282}}]\\n\"])</script>"
    "<script>self.__next_f.push([1,\"2b:T5,{\\\"a\\\":1}\\n\"])</script>"
)


def test_flight_text_reassembles_chunks():
    text = flight_text(SAMPLE_HTML)
    assert "matchHeader" in text


def test_parse_rows_returns_json_values():
    rows = parse_rows(flight_text(SAMPLE_HTML))
    assert "1a" in rows
    assert walk(rows["1a"], "matchHeader") == [{"matchId": 161282}]


def test_parse_rows_handles_text_rows_with_byte_length():
    # The row's declared length is a byte count; a multi-byte character inside
    # must not shift the following row's boundary. "B0éx" is 5 bytes.
    html = '<script>self.__next_f.push([1,"2e:T5,B0\\u00e9x1:1\\n"])</script>'
    rows = parse_rows(flight_text(html))
    assert rows["2e"] == "B0\u00e9x"
    assert rows["1"] == 1


def test_walk_finds_nested_keys():
    obj = {"a": [{"b": {"c": 1}}, {"c": 2}]}
    assert sorted(walk(obj, "c")) == [1, 2]


def test_ttl_cache_hit_and_expiry():
    cache = _TTLCache(ttl=0.05)
    cache.set("k", "v")
    assert cache.get("k") == "v"
    time.sleep(0.1)
    assert cache.get("k") is None


@pytest.mark.skipif(
    os.environ.get("CRICBUZZ_LIVE_TESTS") != "1",
    reason="set CRICBUZZ_LIVE_TESTS=1 to run live integration tests",
)
def test_live_parser_on_homepage():
    client = CricbuzzClient(ttl=5)
    assert client.page("/cricket-match/live-scores")
