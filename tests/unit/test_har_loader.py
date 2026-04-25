"""Tests for the HAR loader."""

from __future__ import annotations

from pathlib import Path

import pytest

from ddf_toolkit.simulator.har_loader import HARLoader, HARLoadError

CAPTURES = Path(__file__).parent.parent / "fixtures" / "captures"


class TestHARLoaderFromFile:
    def test_load_oauth_flow(self):
        loader = HARLoader.from_file(CAPTURES / "microsoft_calendar_oauth_flow.har")
        assert len(loader.entries) == 2
        assert loader.entries[0].request.method == "POST"
        assert loader.entries[1].request.method == "GET"

    def test_load_event_list(self):
        loader = HARLoader.from_file(CAPTURES / "microsoft_calendar_event_list.har")
        assert len(loader.entries) == 2

    def test_load_nonexistent_file(self):
        with pytest.raises(HARLoadError, match="Cannot read"):
            HARLoader.from_file(Path("/nonexistent.har"))


class TestHARLoaderFromJson:
    def test_invalid_json(self):
        with pytest.raises(HARLoadError, match="Invalid JSON"):
            HARLoader.from_json("{broken")

    def test_missing_log(self):
        with pytest.raises(HARLoadError, match="missing 'log'"):
            HARLoader.from_json('{"foo": "bar"}')

    def test_missing_entries(self):
        with pytest.raises(HARLoadError, match="missing 'entries'"):
            HARLoader.from_json('{"log": {"version": "1.2"}}')


class TestHARMatch:
    @pytest.fixture()
    def loader(self):
        return HARLoader.from_file(CAPTURES / "microsoft_calendar_oauth_flow.har")

    def test_exact_match(self, loader):
        resp = loader.match(
            "POST",
            "https://login.microsoftonline.com/tenant-id-here/oauth2/v2.0/token",
        )
        assert resp is not None
        assert resp.status == 200
        assert resp.body["token_type"] == "Bearer"

    def test_no_match(self, loader):
        resp = loader.match("GET", "https://example.com/nonexistent")
        assert resp is None

    def test_method_mismatch(self, loader):
        resp = loader.match(
            "GET",
            "https://login.microsoftonline.com/tenant-id-here/oauth2/v2.0/token",
        )
        assert resp is None

    def test_relaxed_match(self, loader):
        resp = loader.match(
            "GET",
            "https://graph.microsoft.com/v1.0/places/microsoft.graph.room?$select=differentField",
            relaxed=True,
        )
        assert resp is not None
        assert resp.status == 200


class TestHARResponseParsing:
    def test_json_body_parsed(self):
        loader = HARLoader.from_file(CAPTURES / "microsoft_calendar_oauth_flow.har")
        resp = loader.entries[0].response
        assert isinstance(resp.body, dict)
        assert resp.body["access_token"].startswith("eyJ")

    def test_response_headers(self):
        loader = HARLoader.from_file(CAPTURES / "microsoft_calendar_oauth_flow.har")
        resp = loader.entries[0].response
        assert resp.headers["Content-Type"] == "application/json"

    def test_request_headers(self):
        loader = HARLoader.from_file(CAPTURES / "microsoft_calendar_oauth_flow.har")
        req = loader.entries[1].request
        assert req.headers["Accept"] == "application/json"


class TestHAREntryListing:
    def test_list_entries(self):
        loader = HARLoader.from_file(CAPTURES / "microsoft_calendar_oauth_flow.har")
        listing = loader.list_entries()
        assert len(listing) == 2
        assert listing[0]["method"] == "POST"
        assert listing[1]["method"] == "GET"

    def test_event_entries_empty(self):
        loader = HARLoader.from_file(CAPTURES / "microsoft_calendar_oauth_flow.har")
        assert loader.event_entries() == []


class TestHARComments:
    def test_entry_comment(self):
        loader = HARLoader.from_file(CAPTURES / "microsoft_calendar_oauth_flow.har")
        assert "OAuth" in loader.entries[0].comment
