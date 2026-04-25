"""Tests for the DDF Builder — including end-to-end round-trip validation."""

from __future__ import annotations

from pathlib import Path

from ddf_toolkit.bridge.builder import _generate_device_id, build_ddf
from ddf_toolkit.bridge.grouper import group_entities
from ddf_toolkit.bridge.ha_source import HASnapshotSource
from ddf_toolkit.linter import lint_ddf
from ddf_toolkit.parser.parser import parse_ddf
from ddf_toolkit.serializer import serialize_ddf

SNAPSHOTS = Path(__file__).parent.parent / "fixtures" / "ha_snapshots"


class TestDeviceId:
    def test_deterministic(self):
        id1 = _generate_device_id("Sonoff", "Basic R3")
        id2 = _generate_device_id("Sonoff", "Basic R3")
        assert id1 == id2

    def test_different_for_different_input(self):
        id1 = _generate_device_id("Sonoff", "Basic R3")
        id2 = _generate_device_id("Signify", "BSB002")
        assert id1 != id2

    def test_format(self):
        device_id = _generate_device_id("Sonoff", "Basic R3")
        assert device_id.startswith("0x0DFA00")
        assert device_id.endswith("0100")
        assert len(device_id) == 20  # 0x0DFA00 (8) + 8 hex + 0100 (4)


class TestBuildDDF:
    def test_build_switch_ddf(self):
        snapshot = HASnapshotSource(SNAPSHOTS / "test_mixed_devices.json").load()
        groups = group_entities(snapshot)
        sonoff = next(g for g in groups if g.manufacturer == "sonoff")

        ddf = build_ddf(sonoff, snapshot.services)
        assert ddf.general_metadata.manufacturer == "sonoff"
        assert ddf.general_metadata.protocol == "REST-API (DDF)"
        assert len(ddf.config) == 3
        assert len(ddf.commands) >= 1
        assert len(ddf.items) > 0
        assert len(ddf.writes) > 0

    def test_quality_items_present(self):
        snapshot = HASnapshotSource(SNAPSHOTS / "test_mixed_devices.json").load()
        groups = group_entities(snapshot)
        sonoff = next(g for g in groups if g.manufacturer == "sonoff")

        ddf = build_ddf(sonoff, snapshot.services)
        aliases = [i.alias for i in ddf.items]
        assert "QUALITY" in aliases
        assert "QUALITY_TOKEN" in aliases

    def test_device_id_uses_fa_prefix(self):
        snapshot = HASnapshotSource(SNAPSHOTS / "test_mixed_devices.json").load()
        groups = group_entities(snapshot)
        sonoff = next(g for g in groups if g.manufacturer == "sonoff")

        ddf = build_ddf(sonoff, snapshot.services)
        assert ddf.general_metadata.id.startswith("0x0DFA00")


class TestEndToEndRoundTrip:
    """The Lackmus-Probe: Snapshot → Build → Serialize → Re-Parse → Lint."""

    def test_switch_roundtrip_stage1_serialize(self):
        """Stage 1: AST → CSV bytes."""
        snapshot = HASnapshotSource(SNAPSHOTS / "test_mixed_devices.json").load()
        groups = group_entities(snapshot)
        sonoff = next(g for g in groups if g.manufacturer == "sonoff")

        ddf = build_ddf(sonoff, snapshot.services)
        csv = serialize_ddf(ddf)

        assert isinstance(csv, str)
        assert "*GENERAL" in csv
        assert "*WRITE" in csv
        assert "*ITEM" in csv
        assert "GETSTATES" in csv

    def test_switch_roundtrip_stage2_reparse(self):
        """Stage 2: CSV → AST. Structural match."""
        snapshot = HASnapshotSource(SNAPSHOTS / "test_mixed_devices.json").load()
        groups = group_entities(snapshot)
        sonoff = next(g for g in groups if g.manufacturer == "sonoff")

        ddf = build_ddf(sonoff, snapshot.services)
        csv = serialize_ddf(ddf)

        tmp = Path("/tmp/ddf_builder_rt.csv")
        tmp.write_text(csv, encoding="utf-8")
        reparsed = parse_ddf(tmp)

        # Structural checks (filter header pseudo-entries)
        real_items = [i for i in reparsed.items if i.alias.upper() != "ALIAS"]
        real_orig = [i for i in ddf.items if i.alias.upper() != "ALIAS"]
        assert len(real_items) == len(real_orig)

        real_writes = [w for w in reparsed.writes if w.alias.upper() != "ALIAS"]
        real_orig_w = [w for w in ddf.writes if w.alias.upper() != "ALIAS"]
        assert len(real_writes) == len(real_orig_w)

    def test_switch_roundtrip_stage3_lint(self):
        """Stage 3: Lint the re-parsed DDF. Zero errors."""
        snapshot = HASnapshotSource(SNAPSHOTS / "test_mixed_devices.json").load()
        groups = group_entities(snapshot)
        sonoff = next(g for g in groups if g.manufacturer == "sonoff")

        ddf = build_ddf(sonoff, snapshot.services)
        csv = serialize_ddf(ddf)

        tmp = Path("/tmp/ddf_builder_lint.csv")
        tmp.write_text(csv, encoding="utf-8")
        reparsed = parse_ddf(tmp)

        findings = lint_ddf(reparsed)
        errors = [f for f in findings if f.severity == "error"]
        assert len(errors) == 0, f"Lint errors: {errors}"
