"""Tests for the golden-file comparison harness."""

from __future__ import annotations

from pathlib import Path

from ddf_toolkit.golden.runner import (
    FieldDiff,
    GoldenResult,
    discover_golden_fixtures,
    run_golden_test,
)

FIXTURES = Path(__file__).parent.parent / "fixtures"


class TestGoldenResult:
    def test_pass_summary(self):
        r = GoldenResult(passed=True, ddf_name="test.csv", capture_name="test.har")
        assert "PASS" in r.summary()

    def test_fail_summary(self):
        r = GoldenResult(
            passed=False,
            ddf_name="test.csv",
            capture_name="test.har",
            diffs=[FieldDiff(path="items.1", expected=10, actual=20)],
        )
        s = r.summary()
        assert "FAIL" in s
        assert "items.1" in s


class TestDiscoverFixtures:
    def test_discovers_golden_triples(self):
        triples = discover_golden_fixtures(FIXTURES)
        assert len(triples) >= 1
        for ddf, capture, golden in triples:
            assert ddf.exists()
            assert capture.exists()
            assert golden.exists()


class TestRunGoldenTest:
    def test_ms_calendar_oauth_golden(self):
        result = run_golden_test(
            ddf_path=FIXTURES / "ddfs" / "microsoft_calendar.csv",
            capture_path=FIXTURES / "captures" / "microsoft_calendar_oauth_flow.har",
            golden_path=FIXTURES / "golden" / "microsoft_calendar_oauth_flow.json",
            frozen_time=1745571600.0,
            initial_config={"0": "tenant-id-here", "1": "test-client-id", "2": "test-secret"},
            ignore_fields=[
                "gparams",
                "debug_log",
                "http_requests",
                "steps_executed",
                "step_limit_reached",
                "side_effects",
            ],
        )
        assert result.passed, result.summary()
        assert result.simulation is not None
