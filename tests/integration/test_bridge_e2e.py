"""End-to-end integration tests for the HA-Bridge DDF Generator.

ALL 5 STAGES for ALL integration groups from the test snapshot.
Proves bridge.md pattern is executable for every supported domain.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ddf_toolkit.bridge.builder import build_ddf
from ddf_toolkit.bridge.grouper import IntegrationGroup, group_entities
from ddf_toolkit.bridge.ha_source import HASnapshotSource
from ddf_toolkit.linter import lint_ddf
from ddf_toolkit.parser.parser import parse_ddf
from ddf_toolkit.serializer import serialize_ddf
from ddf_toolkit.simulator.har_loader import HARLoader
from ddf_toolkit.simulator.runner import run_simulation

SNAPSHOTS = Path(__file__).parent.parent / "fixtures" / "ha_snapshots"
CAPTURES = Path(__file__).parent.parent / "fixtures" / "captures"

_CONFIG = {"0": "http://homeassistant.local:8123", "1": "test-ha-token", "2": "5000"}


def _build_and_serialize(group: IntegrationGroup, services: dict) -> str:
    """Build DDF from group, serialize to CSV."""
    ddf_ast = build_ddf(group, services)
    return serialize_ddf(ddf_ast)


def _all_groups() -> list[tuple[IntegrationGroup, dict]]:
    """Load all integration groups from the test snapshot."""
    snapshot = HASnapshotSource(SNAPSHOTS / "test_mixed_devices.json").load()
    groups = group_entities(snapshot)
    return [(g, snapshot.services) for g in groups]


def _groups_with_templates() -> list[tuple[str, IntegrationGroup, dict]]:
    """Filter to groups that have at least one supported domain."""
    from ddf_toolkit.bridge.templates import get_template

    result = []
    for group, services in _all_groups():
        domains = {e.domain for e in group.entities}
        has_template = any(get_template(d) is not None for d in domains)
        if has_template:
            result.append((group.name, group, services))
    return result


# -- Per-group parametrized Stage 1-3 tests --


@pytest.mark.parametrize(
    "name,group,services",
    _groups_with_templates(),
    ids=[t[0] for t in _groups_with_templates()],
)
class TestAllGroupsStages123:
    def test_stage1_serialize(self, name: str, group: IntegrationGroup, services: dict) -> None:
        csv = _build_and_serialize(group, services)
        assert "*GENERAL" in csv
        assert "*WRITE" in csv

    def test_stage2_reparse(self, name: str, group: IntegrationGroup, services: dict) -> None:
        csv = _build_and_serialize(group, services)
        tmp = Path(f"/tmp/bridge_e2e_{name.replace(' ', '_')}.csv")
        tmp.write_text(csv, encoding="utf-8")
        reparsed = parse_ddf(tmp)
        real_items = [i for i in reparsed.items if i.alias.upper() != "ALIAS"]
        assert len(real_items) > 0

    def test_stage3_lint(self, name: str, group: IntegrationGroup, services: dict) -> None:
        csv = _build_and_serialize(group, services)
        tmp = Path(f"/tmp/bridge_e2e_{name.replace(' ', '_')}_lint.csv")
        tmp.write_text(csv, encoding="utf-8")
        reparsed = parse_ddf(tmp)
        findings = lint_ddf(reparsed)
        errors = [f for f in findings if f.severity == "error"]
        assert len(errors) == 0, f"Lint errors for {name}: {errors}"


# -- Stage 4: Simulate against HAR (per group) --


@pytest.mark.parametrize(
    "name,group,services",
    _groups_with_templates(),
    ids=[t[0] for t in _groups_with_templates()],
)
class TestAllGroupsStage4:
    def test_stage4_simulate(self, name: str, group: IntegrationGroup, services: dict) -> None:
        csv = _build_and_serialize(group, services)
        tmp = Path(f"/tmp/bridge_e2e_{name.replace(' ', '_')}_sim.csv")
        tmp.write_text(csv, encoding="utf-8")
        ddf = parse_ddf(tmp)

        loader = HARLoader.from_file(CAPTURES / "ha_states_endpoint.har")
        result = run_simulation(
            ddf, loader, step_limit=20, frozen_time=1745571600.0, initial_config=_CONFIG
        )

        assert isinstance(result.items, dict)
        assert not result.step_limit_reached, f"Step limit reached for {name}"


# -- Stage 5: Signing (one representative group) --


class TestSigningRoundTrip:
    def test_stage5_sign_switch(self):
        from ddf_toolkit.signing.keys import generate_test_keypair
        from ddf_toolkit.signing.sign import sign_ddf
        from ddf_toolkit.signing.verify import verify_ddf

        snapshot = HASnapshotSource(SNAPSHOTS / "test_mixed_devices.json").load()
        groups = group_entities(snapshot)
        sonoff = next(g for g in groups if g.manufacturer == "sonoff")
        csv = _build_and_serialize(sonoff, snapshot.services)

        ddf_path = Path("/tmp/bridge_e2e_sign.csv")
        ddf_path.write_text(csv, encoding="utf-8")

        key_path = Path("/tmp/bridge_e2e_key.pem")
        priv, pub = generate_test_keypair(output=key_path)
        signed_path = Path("/tmp/bridge_e2e_signed.csv")
        sign_ddf(ddf_path, key=priv, output=signed_path)

        assert verify_ddf(signed_path, key=pub)
