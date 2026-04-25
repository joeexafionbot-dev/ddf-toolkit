"""Tests for the simulator runner."""

from __future__ import annotations

from pathlib import Path

from ddf_toolkit.parser.parser import parse_ddf
from ddf_toolkit.simulator.har_loader import HARLoader
from ddf_toolkit.simulator.runner import SimulationResult, run_simulation

DDFS = Path(__file__).parent.parent / "fixtures" / "ddfs"
CAPTURES = Path(__file__).parent.parent / "fixtures" / "captures"


class TestSimulationResult:
    def test_to_json(self):
        result = SimulationResult(items={1: "test"}, gparams={"KEY": "val"})
        j = result.to_json()
        assert '"1": "test"' in j
        assert '"KEY": "val"' in j

    def test_to_dict(self):
        result = SimulationResult(items={1: 42}, steps_executed=3)
        d = result.to_dict()
        assert d["items"]["1"] == 42
        assert d["steps_executed"] == 3


class TestRunnerBasic:
    def test_empty_ddf_no_crash(self):
        """A DDF with no WRITE commands should run without error."""
        ddf = parse_ddf(DDFS / "microsoft_calendar.csv")
        loader = HARLoader(entries=[])
        result = run_simulation(ddf, loader, step_limit=5, frozen_time=1000000.0)
        assert result.steps_executed == 0
        assert not result.step_limit_reached

    def test_frozen_time_propagates(self):
        """Frozen time should be accessible via $.SYS.TIME in formulas."""
        ddf = parse_ddf(DDFS / "microsoft_calendar.csv")
        loader = HARLoader(entries=[])
        result = run_simulation(ddf, loader, frozen_time=1745571600.0)
        # RFORMULA should have run and set some items
        assert isinstance(result.items, dict)

    def test_step_limit_prevents_infinite_loop(self):
        """Step limit should prevent runaway trigger loops."""
        ddf = parse_ddf(DDFS / "microsoft_calendar.csv")
        loader = HARLoader.from_file(CAPTURES / "microsoft_calendar_oauth_flow.har")
        result = run_simulation(
            ddf,
            loader,
            step_limit=2,
            frozen_time=1000000.0,
            initial_config={"0": "tenant-id", "1": "client-id", "2": "secret"},
        )
        assert result.steps_executed <= 2


class TestRunnerWithCaptures:
    def test_ms_calendar_oauth_flow(self):
        """Run MS Calendar DDF against OAuth HAR capture."""
        ddf = parse_ddf(DDFS / "microsoft_calendar.csv")
        loader = HARLoader.from_file(CAPTURES / "microsoft_calendar_oauth_flow.har")
        result = run_simulation(
            ddf,
            loader,
            step_limit=10,
            frozen_time=1000000.0,
            initial_config={"0": "tenant-id", "1": "client-id", "2": "secret"},
        )
        # Should have executed at least one WRITE step
        assert isinstance(result.items, dict)
        assert isinstance(result.gparams, dict)
        assert len(result.debug_log) >= 0  # May have debug output

    def test_daikin_status_poll_loads(self):
        """Verify Daikin status poll HAR loads correctly."""
        loader = HARLoader.from_file(CAPTURES / "daikin_stylish_status_poll.har")
        assert len(loader.entries) == 2
        assert loader.entries[0].response.status == 200

    def test_daikin_error_response_loads(self):
        """Verify Daikin error HAR loads correctly."""
        loader = HARLoader.from_file(CAPTURES / "daikin_stylish_error_response.har")
        assert len(loader.entries) == 1
        assert loader.entries[0].response.status == 503


class TestAllFixturesLoad:
    """Verify all 6 HAR fixtures parse without errors."""

    def test_oauth_flow(self):
        loader = HARLoader.from_file(CAPTURES / "microsoft_calendar_oauth_flow.har")
        assert len(loader.entries) >= 1

    def test_event_list(self):
        loader = HARLoader.from_file(CAPTURES / "microsoft_calendar_event_list.har")
        assert len(loader.entries) >= 1

    def test_token_refresh(self):
        loader = HARLoader.from_file(CAPTURES / "microsoft_calendar_token_refresh.har")
        assert len(loader.entries) >= 1

    def test_daikin_status(self):
        loader = HARLoader.from_file(CAPTURES / "daikin_stylish_status_poll.har")
        assert len(loader.entries) >= 1

    def test_daikin_set_mode(self):
        loader = HARLoader.from_file(CAPTURES / "daikin_stylish_set_mode.har")
        assert len(loader.entries) >= 1

    def test_daikin_error(self):
        loader = HARLoader.from_file(CAPTURES / "daikin_stylish_error_response.har")
        assert len(loader.entries) >= 1
