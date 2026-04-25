"""Golden-file comparison harness.

Compares simulation results against expected golden files.
Discovery is filesystem-based: no glue code needed to add a new fixture.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ddf_toolkit.parser.parser import parse_ddf
from ddf_toolkit.simulator.har_loader import HARLoader
from ddf_toolkit.simulator.runner import SimulationResult, run_simulation


@dataclass
class FieldDiff:
    """A single field-level difference."""

    path: str
    expected: Any
    actual: Any


@dataclass
class GoldenResult:
    """Result of comparing simulation output against a golden file."""

    passed: bool
    ddf_name: str = ""
    capture_name: str = ""
    diffs: list[FieldDiff] = field(default_factory=list)
    simulation: SimulationResult | None = None

    def summary(self) -> str:
        if self.passed:
            return f"PASS  {self.ddf_name} vs {self.capture_name}"
        lines = [f"FAIL  {self.ddf_name} vs {self.capture_name} ({len(self.diffs)} diffs)"]
        for d in self.diffs[:20]:
            lines.append(f"  {d.path}: expected={d.expected!r}, got={d.actual!r}")
        if len(self.diffs) > 20:
            lines.append(f"  ... and {len(self.diffs) - 20} more")
        return "\n".join(lines)


def run_golden_test(
    ddf_path: Path,
    capture_path: Path,
    golden_path: Path,
    *,
    frozen_time: float | None = None,
    initial_config: dict[str, Any] | None = None,
    ignore_fields: list[str] | None = None,
) -> GoldenResult:
    """Run a simulation and compare against a golden file.

    Args:
        ddf_path: Path to DDF CSV file
        capture_path: Path to HAR capture file
        golden_path: Path to expected output JSON
        frozen_time: Fixed epoch for deterministic execution
        initial_config: CONFIG values to inject
        ignore_fields: Field paths to skip in comparison (e.g., timestamps)
    """
    ddf = parse_ddf(ddf_path)
    loader = HARLoader.from_file(capture_path)
    golden_raw = json.loads(golden_path.read_text(encoding="utf-8"))
    # Strip metadata keys (prefixed with _)
    golden = {k: v for k, v in golden_raw.items() if not k.startswith("_")}

    result = run_simulation(
        ddf,
        loader,
        frozen_time=frozen_time or 1745571600.0,
        initial_config=initial_config,
    )

    diffs = _compare(golden, result.to_dict(), ignore_fields or [])

    return GoldenResult(
        passed=len(diffs) == 0,
        ddf_name=ddf_path.name,
        capture_name=capture_path.name,
        diffs=diffs,
        simulation=result,
    )


def discover_golden_fixtures(
    fixtures_dir: Path,
) -> list[tuple[Path, Path, Path]]:
    """Discover (ddf, capture, golden) triples from filesystem layout.

    Convention:
        tests/fixtures/ddfs/<name>.csv
        tests/fixtures/captures/<name>_<scenario>.har
        tests/fixtures/golden/<name>_<scenario>.json
    """
    golden_dir = fixtures_dir / "golden"
    captures_dir = fixtures_dir / "captures"
    ddfs_dir = fixtures_dir / "ddfs"

    triples = []
    for golden_file in sorted(golden_dir.glob("*.json")):
        stem = golden_file.stem
        capture_file = captures_dir / f"{stem}.har"
        if not capture_file.exists():
            continue

        # Derive DDF name: strip scenario suffix
        # e.g., "microsoft_calendar_oauth_flow" -> "microsoft_calendar"
        parts = stem.split("_")
        for i in range(len(parts), 0, -1):
            candidate = "_".join(parts[:i])
            ddf_file = ddfs_dir / f"{candidate}.csv"
            if ddf_file.exists():
                triples.append((ddf_file, capture_file, golden_file))
                break

    return triples


def _compare(
    expected: dict[str, Any],
    actual: dict[str, Any],
    ignore: list[str],
    prefix: str = "",
) -> list[FieldDiff]:
    """Recursively compare expected vs actual, returning diffs."""
    diffs: list[FieldDiff] = []

    for key, exp_val in expected.items():
        path = f"{prefix}.{key}" if prefix else key
        if path in ignore:
            continue

        act_val = actual.get(key)

        if isinstance(exp_val, dict) and isinstance(act_val, dict):
            diffs.extend(_compare(exp_val, act_val, ignore, path))
        elif str(exp_val) != str(act_val):
            diffs.append(FieldDiff(path=path, expected=exp_val, actual=act_val))

    return diffs
