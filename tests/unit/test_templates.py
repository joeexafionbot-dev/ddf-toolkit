"""Tests for domain templates — light, cover, fan, sensor, binary_sensor, lock."""

from __future__ import annotations

from ddf_toolkit.bridge.models import HAEntity
from ddf_toolkit.bridge.templates.binary_sensor import BinarySensorTemplate
from ddf_toolkit.bridge.templates.cover import CoverTemplate
from ddf_toolkit.bridge.templates.fan import FanTemplate
from ddf_toolkit.bridge.templates.light import LightTemplate
from ddf_toolkit.bridge.templates.lock import LockTemplate
from ddf_toolkit.bridge.templates.sensor import SensorTemplate


class TestLightTemplate:
    def test_can_handle(self):
        t = LightTemplate()
        assert t.can_handle(HAEntity(entity_id="light.x", state="on", domain="light"))
        assert not t.can_handle(HAEntity(entity_id="switch.x", state="on", domain="switch"))

    def test_build_items_basic(self):
        t = LightTemplate()
        entities = [
            HAEntity(
                entity_id="light.bulb",
                state="on",
                domain="light",
                attributes={"friendly_name": "Bulb", "supported_features": 0},
            ),
        ]
        items = t.build_items(entities)
        # state + command = 2 items (no brightness/color_temp without features)
        assert len(items) == 2
        assert items[0].alias == "LIGHT_BULB"

    def test_build_items_with_brightness(self):
        t = LightTemplate()
        entities = [
            HAEntity(
                entity_id="light.bulb",
                state="on",
                domain="light",
                attributes={"friendly_name": "Bulb", "supported_features": 1, "brightness": 200},
            ),
        ]
        items = t.build_items(entities)
        aliases = [i.alias for i in items]
        assert "LIGHT_BULB_BRIGHTNESS" in aliases

    def test_build_items_with_color_temp(self):
        t = LightTemplate()
        entities = [
            HAEntity(
                entity_id="light.bulb",
                state="on",
                domain="light",
                attributes={"friendly_name": "Bulb", "supported_features": 3, "brightness": 200, "color_temp": 370},
            ),
        ]
        items = t.build_items(entities)
        aliases = [i.alias for i in items]
        assert "LIGHT_BULB_BRIGHTNESS" in aliases
        assert "LIGHT_BULB_COLOR_TEMP" in aliases

    def test_build_writes(self):
        t = LightTemplate()
        writes = t.build_writes(
            [HAEntity(entity_id="light.x", state="on", domain="light")], []
        )
        aliases = [w.alias for w in writes]
        assert "GETSTATES" in aliases
        assert "SVC_LIGHT_TURN_ON" in aliases
        assert "SVC_LIGHT_TURN_OFF" in aliases


class TestCoverTemplate:
    def test_can_handle(self):
        t = CoverTemplate()
        assert t.can_handle(HAEntity(entity_id="cover.x", state="open", domain="cover"))

    def test_build_items(self):
        t = CoverTemplate()
        entities = [
            HAEntity(
                entity_id="cover.blinds",
                state="open",
                domain="cover",
                attributes={"friendly_name": "Blinds", "current_position": 100},
            ),
        ]
        items = t.build_items(entities)
        aliases = [i.alias for i in items]
        assert "COVER_BLINDS" in aliases
        assert "COVER_BLINDS_POS" in aliases
        assert "COVER_BLINDS_CMD" in aliases

    def test_build_writes(self):
        t = CoverTemplate()
        writes = t.build_writes(
            [HAEntity(entity_id="cover.x", state="open", domain="cover")], []
        )
        aliases = [w.alias for w in writes]
        assert "SVC_OPEN_COVER" in aliases
        assert "SVC_CLOSE_COVER" in aliases
        assert "SVC_STOP_COVER" in aliases


class TestFanTemplate:
    def test_can_handle(self):
        t = FanTemplate()
        assert t.can_handle(HAEntity(entity_id="fan.x", state="on", domain="fan"))

    def test_build_items(self):
        t = FanTemplate()
        entities = [
            HAEntity(
                entity_id="fan.ceiling",
                state="on",
                domain="fan",
                attributes={"friendly_name": "Ceiling Fan", "percentage": 50},
            ),
        ]
        items = t.build_items(entities)
        aliases = [i.alias for i in items]
        assert "FAN_CEILING" in aliases
        assert "FAN_CEILING_PCT" in aliases
        assert "FAN_CEILING_CMD" in aliases

    def test_build_writes(self):
        t = FanTemplate()
        writes = t.build_writes(
            [HAEntity(entity_id="fan.x", state="on", domain="fan")], []
        )
        aliases = [w.alias for w in writes]
        assert "SVC_FAN_TURN_ON" in aliases
        assert "SVC_FAN_TURN_OFF" in aliases


class TestSensorTemplate:
    def test_build_items_with_unit(self):
        t = SensorTemplate()
        entities = [
            HAEntity(
                entity_id="sensor.temp",
                state="22.5",
                domain="sensor",
                attributes={"friendly_name": "Temp", "unit_of_measurement": "°C"},
            ),
        ]
        items = t.build_items(entities)
        assert len(items) == 1
        assert items[0].unit == "°C"
        assert "GETSTATES" in (items[0].rformula or "")

    def test_read_only(self):
        t = SensorTemplate()
        writes = t.build_writes(
            [HAEntity(entity_id="sensor.x", state="0", domain="sensor")], []
        )
        assert len(writes) == 1  # Only GETSTATES, no service calls


class TestBinarySensorTemplate:
    def test_boolean_mapping(self):
        t = BinarySensorTemplate()
        entities = [
            HAEntity(
                entity_id="binary_sensor.motion",
                state="on",
                domain="binary_sensor",
                attributes={"friendly_name": "Motion"},
            ),
        ]
        items = t.build_items(entities)
        assert len(items) == 1
        assert "ISEQUAL" in (items[0].rformula or "")
        assert "'on'" in (items[0].rformula or "")


class TestLockTemplate:
    def test_build_items(self):
        t = LockTemplate()
        entities = [
            HAEntity(
                entity_id="lock.door",
                state="locked",
                domain="lock",
                attributes={"friendly_name": "Door"},
            ),
        ]
        items = t.build_items(entities)
        aliases = [i.alias for i in items]
        assert "LOCK_DOOR" in aliases
        assert "LOCK_DOOR_CMD" in aliases

    def test_locked_mapping(self):
        t = LockTemplate()
        entities = [
            HAEntity(entity_id="lock.door", state="locked", domain="lock"),
        ]
        items = t.build_items(entities)
        state_item = items[0]
        assert "'locked'" in (state_item.rformula or "")
