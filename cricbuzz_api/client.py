"""Low-level HTTP client and Next.js RSC (React Server Components) parser.

cricbuzz.com is a Next.js App Router site. Every page ships its server-side
props as a stream of ``self.__next_f.push([1, "<json-string>"])`` calls in the
HTML. Reassembling and unescaping those chunks yields the RSC "flight" payload,
which contains the structured data (matches, scorecards, commentary, ...) that
we expose through the API.
"""

from __future__ import annotations

import json
import re
import threading
import time
import urllib.error
import urllib.request
from typing import Any

BASE_URL = "https://www.cricbuzz.com"

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

_PUSH_RE = re.compile(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)', re.S)
_ROW_RE = re.compile(r'([0-9a-f]+):')
_WS = " \n\t\r"
_DECODER = json.JSONDecoder()


class CricbuzzError(RuntimeError):
    """Raised when a cricbuzz page cannot be fetched or parsed."""


class _TTLCache:
    """A tiny thread-safe TTL cache keyed by string."""

    def __init__(self, ttl: float, maxsize: int = 512) -> None:
        self.ttl = ttl
        self.maxsize = maxsize
        self._data: dict[str, tuple[float, Any]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Any | None:
        with self._lock:
            item = self._data.get(key)
            if item is None:
                return None
            expires, value = item
            if expires < time.time():
                self._data.pop(key, None)
                return None
            return value

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            if len(self._data) >= self.maxsize:
                now = time.time()
                for k in [k for k, (exp, _) in self._data.items() if exp < now]:
                    self._data.pop(k, None)
                while len(self._data) >= self.maxsize:
                    self._data.pop(next(iter(self._data)))
            self._data[key] = (time.time() + self.ttl, value)


def fetch_html(path: str, timeout: float = 25.0) -> str:
    """Fetch a path (or absolute URL) from cricbuzz and return the HTML."""
    url = path if path.startswith("http") else BASE_URL + path
    req = urllib.request.Request(url, headers=DEFAULT_HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        raise CricbuzzError(f"HTTP {exc.code} for {url}") from exc
    except urllib.error.URLError as exc:
        raise CricbuzzError(f"Network error for {url}: {exc.reason}") from exc


def flight_text(html: str) -> str:
    """Reassemble the RSC flight payload from a Next.js page's HTML."""
    chunks = _PUSH_RE.findall(html)
    if not chunks:
        raise CricbuzzError("No Next.js RSC payload found in page")
    raw = "".join(chunks)
    try:
        return json.loads('"' + raw + '"')
    except json.JSONDecodeError:
        # Fall back to a lenient escape decode if the stream is malformed.
        return raw.encode("utf-8", "surrogatepass").decode("unicode_escape")


def parse_rows(text: str) -> dict[str, Any]:
    """Parse the flight stream into a ``{row_id: value}`` mapping.

    Rows look like ``<hex-id>:<value>`` where the value is either raw JSON, a
    text row (``T<hex-len>,<text>``) or a module reference (``I...``) that we
    skip. Text rows carry their byte length after the ``T`` marker, which lets
    us slice them out even when they are not valid JSON on their own.
    """
    rows: dict[str, Any] = {}
    pos = 0
    n = len(text)
    while pos < n:
        while pos < n and text[pos] in _WS:
            pos += 1
        match = _ROW_RE.match(text, pos)
        if not match:
            newline = text.find("\n", pos)
            pos = newline + 1 if newline >= 0 else n
            continue
        row_id = match.group(1)
        cursor = match.end()
        if cursor < n and text[cursor] == "T":
            marker = re.match(r"T([0-9a-f]+),", text[cursor:])
            if not marker:
                newline = text.find("\n", pos)
                pos = newline + 1 if newline >= 0 else n
                continue
            # The marker length is a byte count; slice the UTF-8 encoding so
            # multi-byte characters do not shift the following row boundary.
            length = int(marker.group(1), 16)
            start = cursor + marker.end()
            content = text[start:].encode("utf-8")[:length].decode("utf-8", "replace")
            try:
                rows[row_id] = _DECODER.raw_decode(content)[0]
            except json.JSONDecodeError:
                rows[row_id] = content
            pos = start + len(content)
            continue
        if cursor < n and text[cursor] == "I":
            newline = text.find("\n", cursor)
            pos = newline + 1 if newline >= 0 else n
            continue
        try:
            value, end = _DECODER.raw_decode(text, cursor)
        except json.JSONDecodeError:
            newline = text.find("\n", cursor)
            pos = newline + 1 if newline >= 0 else n
            continue
        rows[row_id] = value
        pos = end
    return rows


def walk(obj: Any, key: str) -> list[Any]:
    """Return every value stored under ``key`` anywhere in a nested object."""
    found: list[Any] = []
    stack: list[Any] = [obj]
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            for k, v in node.items():
                if k == key:
                    found.append(v)
                stack.append(v)
        elif isinstance(node, list):
            stack.extend(node)
    return found


def _looks_like_payload(value: Any) -> bool:
    return isinstance(value, (dict, list)) and len(value) > 0


class CricbuzzClient:
    """Fetches and caches parsed cricbuzz pages."""

    def __init__(self, ttl: float = 30.0, timeout: float = 25.0) -> None:
        self.ttl = ttl
        self.timeout = timeout
        self._cache = _TTLCache(ttl)

    def page(self, path: str) -> dict[str, Any]:
        """Return the parsed flight rows for a page (cached)."""
        cache_key = "rows:" + path
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        rows = parse_rows(flight_text(fetch_html(path, self.timeout)))
        self._cache.set(cache_key, rows)
        return rows

    def extract(self, path: str, key: str, *, required: bool = True) -> Any:
        """Return the first non-empty value found under ``key`` on a page."""
        cached = self._cache.get(f"key:{key}:{path}")
        if cached is not None:
            return cached
        value = None
        for row in self.page(path).values():
            matches = [m for m in walk(row, key) if _looks_like_payload(m)]
            if matches:
                value = matches[0]
                break
        if value is None and required:
            raise CricbuzzError(f"Key '{key}' not found at {path}")
        self._cache.set(f"key:{key}:{path}", value)
        return value

    def extract_all(self, path: str, key: str) -> list[Any]:
        """Return all non-empty values found under ``key`` on a page."""
        cached = self._cache.get(f"all:{key}:{path}")
        if cached is not None:
            return cached
        results: list[Any] = []
        for row in self.page(path).values():
            results.extend(m for m in walk(row, key) if _looks_like_payload(m))
        self._cache.set(f"all:{key}:{path}", results)
        return results

    def json_ld(self, path: str) -> list[dict[str, Any]]:
        """Extract every JSON-LD (schema.org) block from a page.

        Blocks appear either as raw JSON or as an escaped JSON string embedded
        inside an RSC text row; both forms are handled.
        """
        cached = self._cache.get(f"ld:{path}")
        if cached is not None:
            return cached
        text = flight_text(fetch_html(path, self.timeout))
        blocks: list[dict[str, Any]] = []
        for match in re.finditer(r'\{"@context":"https://schema\.org"', text):
            try:
                value, _ = _DECODER.raw_decode(text, match.start())
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                blocks.append(value)
        escaped = re.compile(r'"\{\\"@context\\":\\"https://schema\.org.*?\}"', re.S)
        for match in escaped.finditer(text):
            try:
                # The match is a JSON string literal wrapping the JSON-LD text.
                value = json.loads(json.loads(match.group(0)))
            except (json.JSONDecodeError, ValueError):
                continue
            if isinstance(value, dict):
                blocks.append(value)
        self._cache.set(f"ld:{path}", blocks)
        return blocks

    def first_json_ld(self, path: str, type_name: str) -> dict[str, Any] | None:
        for block in self.json_ld(path):
            if block.get("@type") == type_name:
                return block
        return None
