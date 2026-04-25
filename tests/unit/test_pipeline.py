"""Tests for the Round-Trip Pipeline and Snapshot Anonymizer."""

from __future__ import annotations

from pathlib import Path

import pytest

from ddf_toolkit.bridge.anonymizer import anonymize_snapshot, verify_anonymized
from ddf_toolkit.bridge.grouper import group_entities
from ddf_toolkit.bridge.ha_source import HASnapshotSource
from ddf_toolkit.bridge.pipeline import RoundTripPipeline
from ddf_toolkit.simulator.har_loader import HARLoader

SNAPSHOTS = Path(__file__).parent.parent / "fixtures" / "ha_snapshots"
CAPTURES = Path(__file__).parent.parent / "fixtures" / "captures"


class TestPipelineAllGroups:
    """Pipeline validates every integration group through all 5 stages."""

    @pytest.fixture()
    def pipeline(self):
        loader = HARLoader.from_file(CAPTURES / "ha_states_endpoint.har")
        return RoundTripPipeline(har_loader=loader)

    @pytest.fixture()
    def snapshot(self):
        return HASnapshotSource(SNAPSHOTS / "test_mixed_devices.json").load()

    def test_all_groups_pass(self, pipeline, snapshot):
        groups = group_entities(snapshot)
        from ddf_toolkit.bridge.templates import get_template

        for group in groups:
            has_template = any(get_template(e.domain) for e in group.entities)
            if not has_template:
                continue
            report = pipeline.validate(group, snapshot.services)
            assert report.passed, f"Pipeline failed for {group.name}:\n{report.summary()}"

    def test_report_summary(self, pipeline, snapshot):
        groups = group_entities(snapshot)
        sonoff = next(g for g in groups if g.manufacturer == "sonoff")
        report = pipeline.validate(sonoff, snapshot.services)
        summary = report.summary()
        assert "PASS" in summary
        assert "serialize" in summary
        assert "sign" in summary

    def test_all_5_stages_run(self, pipeline, snapshot):
        groups = group_entities(snapshot)
        sonoff = next(g for g in groups if g.manufacturer == "sonoff")
        report = pipeline.validate(sonoff, snapshot.services)
        assert len(report.stages) == 5
        stage_names = [s.name for s in report.stages]
        assert stage_names == ["serialize", "reparse", "lint", "simulate", "sign"]


class TestPipelineWithoutHAR:
    def test_stage4_skipped_without_har(self):
        pipeline = RoundTripPipeline(har_loader=None)
        snapshot = HASnapshotSource(SNAPSHOTS / "test_mixed_devices.json").load()
        groups = group_entities(snapshot)
        sonoff = next(g for g in groups if g.manufacturer == "sonoff")
        report = pipeline.validate(sonoff, snapshot.services)
        assert report.passed
        sim_stage = next(s for s in report.stages if s.name == "simulate")
        assert "skipped" in (sim_stage.error or "")


class TestAnonymizer:
    @pytest.fixture()
    def raw_snapshot(self):
        import json

        return json.loads((SNAPSHOTS / "test_mixed_devices.json").read_text(encoding="utf-8"))

    def test_entity_ids_pseudonymized(self, raw_snapshot):
        anon = anonymize_snapshot(raw_snapshot)
        for entity in anon["entities"]:
            # Should not contain original entity names
            assert "location_a_plug" not in entity["entity_id"]
            assert "location_" in entity["entity_id"]

    def test_friendly_names_replaced(self, raw_snapshot):
        anon = anonymize_snapshot(raw_snapshot)
        for entity in anon["entities"]:
            fn = entity.get("attributes", {}).get("friendly_name", "")
            if fn:
                assert "Plug A" not in fn
                assert "Bulb A" not in fn
                assert "Device dev_" in fn

    def test_device_names_replaced(self, raw_snapshot):
        anon = anonymize_snapshot(raw_snapshot)
        for device in anon["devices"]:
            assert "Sonoff Basic" not in device["name"]
            assert "Device " in device["name"]

    def test_manufacturer_model_preserved(self, raw_snapshot):
        anon = anonymize_snapshot(raw_snapshot)
        manufacturers = {d["manufacturer"] for d in anon["devices"]}
        assert "Sonoff" in manufacturers
        assert "Signify" in manufacturers

    def test_areas_anonymized(self, raw_snapshot):
        anon = anonymize_snapshot(raw_snapshot)
        for device in anon["devices"]:
            assert "location_a" not in device.get("area", "")
            assert "area_" in device.get("area", "")

    def test_location_stripped(self, raw_snapshot):
        anon = anonymize_snapshot(raw_snapshot)
        assert anon["config"]["location_name"] == "Anonymized Home"
        assert "latitude" not in anon["config"]

    def test_deterministic(self, raw_snapshot):
        anon1 = anonymize_snapshot(raw_snapshot, seed="test")
        anon2 = anonymize_snapshot(raw_snapshot, seed="test")
        assert anon1 == anon2

    def test_different_seed_different_output(self, raw_snapshot):
        anon1 = anonymize_snapshot(raw_snapshot, seed="seed1")
        anon2 = anonymize_snapshot(raw_snapshot, seed="seed2")
        assert anon1["entities"][0]["entity_id"] != anon2["entities"][0]["entity_id"]

    def test_verify_catches_leaks(self):
        """An intentionally leaky snapshot should fail verification."""
        leaky = {
            "entities": [
                {
                    "entity_id": "light.martins_bedroom",
                    "state": "on",
                    "attributes": {
                        "friendly_name": "Martin's Bedroom Light",
                        "ip_address": "192.168.1.42",
                    },
                }
            ],
            "devices": [],
            "config": {"location_name": "Martin Mair's House"},
        }
        violations = verify_anonymized(leaky)
        assert len(violations) > 0
        violation_text = " ".join(violations)
        assert (
            "Martin" in violation_text
            or "bedroom" in violation_text.lower()
            or "192.168" in violation_text
        )

    def test_verify_clean_after_anonymize(self, raw_snapshot):
        anon = anonymize_snapshot(raw_snapshot)
        violations = verify_anonymized(anon)
        assert len(violations) == 0, "Violations found:\n" + "\n".join(violations)
