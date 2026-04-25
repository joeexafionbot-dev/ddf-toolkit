"""Tests for the HA Source Adapter and Grouper."""

from __future__ import annotations

from pathlib import Path

import pytest

from ddf_toolkit.bridge.grouper import group_entities
from ddf_toolkit.bridge.ha_source import HASnapshotSource, HASourceError
from ddf_toolkit.bridge.models import HAEntity

SNAPSHOTS = Path(__file__).parent.parent / "fixtures" / "ha_snapshots"


class TestSnapshotSource:
    def test_load_mixed_devices(self):
        source = HASnapshotSource(SNAPSHOTS / "test_mixed_devices.json")
        snapshot = source.load()
        assert len(snapshot.entities) == 14
        assert len(snapshot.devices) == 9
        assert snapshot.ha_version == "2026.1.4"

    def test_entity_domains(self):
        source = HASnapshotSource(SNAPSHOTS / "test_mixed_devices.json")
        snapshot = source.load()
        domains = {e.domain for e in snapshot.entities}
        assert "switch" in domains
        assert "light" in domains
        assert "sensor" in domains
        assert "climate" in domains

    def test_device_mapping(self):
        source = HASnapshotSource(SNAPSHOTS / "test_mixed_devices.json")
        snapshot = source.load()
        sonoff_entities = [e for e in snapshot.entities if e.device_id == "dev_sonoff_1"]
        assert len(sonoff_entities) == 2

    def test_entity_without_device(self):
        source = HASnapshotSource(SNAPSHOTS / "test_mixed_devices.json")
        snapshot = source.load()
        no_device = [e for e in snapshot.entities if e.device_id is None]
        assert len(no_device) == 1  # helper_uptime

    def test_load_nonexistent(self):
        with pytest.raises(HASourceError, match="Cannot load"):
            HASnapshotSource(Path("/nonexistent.json")).load()

    def test_services_loaded(self):
        source = HASnapshotSource(SNAPSHOTS / "test_mixed_devices.json")
        snapshot = source.load()
        assert "switch" in snapshot.services
        assert len(snapshot.services["switch"]) == 3


class TestGrouper:
    @pytest.fixture()
    def snapshot(self):
        return HASnapshotSource(SNAPSHOTS / "test_mixed_devices.json").load()

    def test_groups_by_manufacturer(self, snapshot):
        groups = group_entities(snapshot)
        manufacturers = {g.manufacturer for g in groups}
        assert "sonoff" in manufacturers
        assert "signify" in manufacturers
        assert "aqara" in manufacturers

    def test_unknown_group_for_deviceless(self, snapshot):
        groups = group_entities(snapshot)
        unknown = [g for g in groups if g.manufacturer == "_unknown"]
        assert len(unknown) == 1
        assert len(unknown[0].entities) == 1  # helper_uptime

    def test_all_entities_assigned(self, snapshot):
        groups = group_entities(snapshot)
        total = sum(len(g.entities) for g in groups)
        assert total == len(snapshot.entities)

    def test_no_group_exceeds_limit(self, snapshot):
        groups = group_entities(snapshot)
        for g in groups:
            assert len(g.entities) <= 25

    def test_deterministic_output(self, snapshot):
        groups1 = group_entities(snapshot)
        groups2 = group_entities(snapshot)
        assert [g.key for g in groups1] == [g.key for g in groups2]

    def test_group_name(self, snapshot):
        groups = group_entities(snapshot)
        sonoff = next(g for g in groups if g.manufacturer == "sonoff")
        assert "sonoff" in sonoff.name
        assert "basic r3" in sonoff.name


class TestSwitchTemplate:
    def test_build_items(self):
        from ddf_toolkit.bridge.templates.switch import SwitchTemplate

        template = SwitchTemplate()
        entities = [
            HAEntity(
                entity_id="switch.plug_a",
                state="on",
                domain="switch",
                attributes={"friendly_name": "Plug A"},
            ),
            HAEntity(
                entity_id="switch.plug_b",
                state="off",
                domain="switch",
                attributes={"friendly_name": "Plug B"},
            ),
        ]
        items = template.build_items(entities)
        assert len(items) == 4  # 2 state + 2 command items
        aliases = [i.alias for i in items]
        assert "SWITCH_PLUG_A" in aliases
        assert "SWITCH_PLUG_A_CMD" in aliases

    def test_build_writes(self):
        from ddf_toolkit.bridge.templates.switch import SwitchTemplate

        template = SwitchTemplate()
        entities = [
            HAEntity(entity_id="switch.plug_a", state="on", domain="switch"),
        ]
        writes = template.build_writes(entities, [])
        assert len(writes) == 3  # GETSTATES + turn_on + turn_off
        aliases = [w.alias for w in writes]
        assert "GETSTATES" in aliases
        assert "SVC_TURN_ON" in aliases
        assert "SVC_TURN_OFF" in aliases

    def test_getstates_has_args(self):
        from ddf_toolkit.bridge.templates.switch import SwitchTemplate

        template = SwitchTemplate()
        writes = template.build_writes(
            [HAEntity(entity_id="switch.x", state="on", domain="switch")], []
        )
        getstates = next(w for w in writes if w.alias == "GETSTATES")
        assert len(getstates.args) == 2  # url + auth header

    def test_can_handle(self):
        from ddf_toolkit.bridge.templates.switch import SwitchTemplate

        t = SwitchTemplate()
        assert t.can_handle(HAEntity(entity_id="switch.x", state="on", domain="switch"))
        assert not t.can_handle(HAEntity(entity_id="light.x", state="on", domain="light"))

    def test_item_rformula_references_getstates(self):
        from ddf_toolkit.bridge.templates.switch import SwitchTemplate

        template = SwitchTemplate()
        entities = [HAEntity(entity_id="switch.plug", state="on", domain="switch")]
        items = template.build_items(entities)
        state_item = next(i for i in items if "CMD" not in i.alias)
        assert state_item.rformula is not None
        assert "GETSTATES" in state_item.rformula

    def test_error_handling_in_service_formula(self):
        from ddf_toolkit.bridge.templates.switch import SwitchTemplate

        template = SwitchTemplate()
        writes = template.build_writes(
            [HAEntity(entity_id="switch.x", state="on", domain="switch")], []
        )
        svc = next(w for w in writes if w.alias == "SVC_TURN_ON")
        assert "401" in svc.formula  # handles token expired
        assert "DEBUG" in svc.formula  # uses DEBUG for logging
        assert ".F := 0" in svc.formula  # resets trigger

    def test_alias_collision_detection(self):
        from ddf_toolkit.bridge.templates.common import deduplicate_aliases

        seen: set[str] = set()
        a1 = deduplicate_aliases("SWITCH_PLUG", seen)
        seen.add(a1)
        assert a1 == "SWITCH_PLUG"

        a2 = deduplicate_aliases("SWITCH_PLUG", seen)
        seen.add(a2)
        assert a2 == "SWITCH_PLUG_2"

        a3 = deduplicate_aliases("SWITCH_PLUG", seen)
        seen.add(a3)
        assert a3 == "SWITCH_PLUG_3"
