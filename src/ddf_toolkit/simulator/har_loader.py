"""HAR 1.2 loader — parse HAR files and expose request/response lookups.

HAR (HTTP Archive) format: https://w3c.github.io/web-performance/specs/HAR/Overview.html
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse


@dataclass(frozen=True)
class HARRequest:
    method: str
    url: str
    headers: dict[str, str]
    body: str
    comment: str = ""


@dataclass(frozen=True)
class HARResponse:
    status: int
    headers: dict[str, str]
    body: Any
    body_raw: str = ""
    comment: str = ""


@dataclass(frozen=True)
class HAREntry:
    request: HARRequest
    response: HARResponse
    comment: str = ""
    simulated_event: bool = False
    event_delay_ms: int = 0


class HARLoadError(Exception):
    pass


@dataclass
class HARLoader:
    """Load and index HAR entries for request/response lookup."""

    entries: list[HAREntry] = field(default_factory=list)
    source_path: str = ""

    @classmethod
    def from_file(cls, path: Path) -> HARLoader:
        """Load a HAR file from disk."""
        try:
            raw = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            msg = f"Cannot read HAR file {path}: {e}"
            raise HARLoadError(msg) from e

        return cls.from_json(raw, source_path=str(path))

    @classmethod
    def from_json(cls, raw: str, source_path: str = "") -> HARLoader:
        """Parse HAR JSON string."""
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            msg = f"Invalid JSON in HAR file: {e}"
            raise HARLoadError(msg) from e

        if "log" not in data:
            msg = "HAR file missing 'log' key"
            raise HARLoadError(msg)

        log = data["log"]
        if "entries" not in log:
            msg = "HAR log missing 'entries' key"
            raise HARLoadError(msg)

        entries: list[HAREntry] = []
        for i, entry_data in enumerate(log["entries"]):
            try:
                entries.append(_parse_entry(entry_data))
            except (KeyError, TypeError) as e:
                msg = f"Invalid HAR entry #{i}: {e}"
                raise HARLoadError(msg) from e

        return cls(entries=entries, source_path=source_path)

    def match(
        self,
        method: str,
        url: str,
        *,
        relaxed: bool = False,
    ) -> HARResponse | None:
        """Find a matching response for the given request.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Full URL
            relaxed: If True, match by path only (ignore query params)

        Returns:
            Matching HARResponse, or None if no match found.
        """
        method_upper = method.upper()

        for entry in self.entries:
            if entry.simulated_event:
                continue
            if entry.request.method.upper() != method_upper:
                continue

            if relaxed:
                if _url_path(entry.request.url) == _url_path(url):
                    return entry.response
            else:
                if _normalize_url(entry.request.url) == _normalize_url(url):
                    return entry.response

        return None

    def event_entries(self) -> list[HAREntry]:
        """Get entries marked as simulated events (for listener injection)."""
        return [e for e in self.entries if e.simulated_event]

    def list_entries(self) -> list[dict[str, str]]:
        """List all entries as summary dicts (for CLI display)."""
        result = []
        for i, entry in enumerate(self.entries):
            result.append(
                {
                    "index": str(i),
                    "method": entry.request.method,
                    "url": entry.request.url,
                    "status": str(entry.response.status),
                    "comment": entry.comment,
                    "event": str(entry.simulated_event),
                }
            )
        return result


def _parse_entry(data: dict[str, Any]) -> HAREntry:
    """Parse a single HAR entry."""
    req_data = data["request"]
    resp_data = data["response"]

    # Request
    headers = {}
    for h in req_data.get("headers", []):
        headers[h["name"]] = h["value"]

    body = ""
    if "postData" in req_data:
        body = req_data["postData"].get("text", "")

    request = HARRequest(
        method=req_data["method"],
        url=req_data["url"],
        headers=headers,
        body=body,
        comment=req_data.get("comment", ""),
    )

    # Response
    resp_headers = {}
    for h in resp_data.get("headers", []):
        resp_headers[h["name"]] = h["value"]

    resp_body_raw = ""
    resp_body: Any = None
    content = resp_data.get("content", {})
    if content.get("text"):
        resp_body_raw = content["text"]
        mime = content.get("mimeType", "")
        if "json" in mime:
            try:
                resp_body = json.loads(resp_body_raw)
            except json.JSONDecodeError:
                resp_body = resp_body_raw
        else:
            resp_body = resp_body_raw

    response = HARResponse(
        status=resp_data["status"],
        headers=resp_headers,
        body=resp_body,
        body_raw=resp_body_raw,
        comment=resp_data.get("comment", ""),
    )

    return HAREntry(
        request=request,
        response=response,
        comment=data.get("comment", ""),
        simulated_event=data.get("_simulated_event", False),
        event_delay_ms=data.get("_event_delay_ms", 0),
    )


def _normalize_url(url: str) -> str:
    """Normalize URL for comparison (lowercase scheme/host, sort query params)."""
    parsed = urlparse(url)
    params = parse_qs(parsed.query, keep_blank_values=True)
    sorted_query = "&".join(f"{k}={v[0]}" for k, v in sorted(params.items()))
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{sorted_query}".rstrip("?")


def _url_path(url: str) -> str:
    """Extract just the path from a URL."""
    return urlparse(url).path
