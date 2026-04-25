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
                attributes={
                    "friendly_name": "Bulb",
                    "supported_features": 3,
                    "brightness": 200,
                    "color_temp": 370,
                },
            ),
        ]
        items = t.build_items(entities)
        aliases = [i.alias for i in items]
        assert "LIGHT_BULB_BRIGHTNESS" in aliases
        assert "LIGHT_BULB_COLOR_TEMP" in aliases

    def test_build_writes(self):
        t = LightTemplate()
        writes = t.build_writes([HAEntity(entity_id="light.x", state="on", domain="light")], [])
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
        writes = t.build_writes([HAEntity(entity_id="cover.x", state="open", domain="cover")], [])
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
        writes = t.build_writes([HAEntity(entity_id="fan.x", state="on", domain="fan")], [])
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
        writes = t.build_writes([HAEntity(entity_id="sensor.x", state="0", domain="sensor")], [])
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


class TestClimateTemplate:
    def test_build_items(self):
        from ddf_toolkit.bridge.templates.climate import ClimateTemplate

        t = ClimateTemplate()
        entities = [
            HAEntity(
                entity_id="climate.thermo",
                state="heat",
                domain="climate",
                attributes={
                    "friendly_name": "Thermostat",
                    "current_temperature": 19.5,
                    "temperature": 21.0,
                    "fan_modes": ["auto", "low"],
                },
            ),
        ]
        items = t.build_items(entities)
        aliases = [i.alias for i in items]
        assert "CLIMATE_THERMO_TEMP" in aliases
        assert "CLIMATE_THERMO_SETPOINT" in aliases
        assert "CLIMATE_THERMO_MODE" in aliases
        assert "CLIMATE_THERMO_FAN" in aliases

    def test_build_writes(self):
        from ddf_toolkit.bridge.templates.climate import ClimateTemplate

        t = ClimateTemplate()
        writes = t.build_writes(
            [HAEntity(entity_id="climate.x", state="heat", domain="climate")], []
        )
        aliases = [w.alias for w in writes]
        assert "SVC_SET_TEMPERATURE" in aliases
        assert "SVC_SET_HVAC_MODE" in aliases


class TestMediaPlayerTemplate:
    def test_build_items(self):
        from ddf_toolkit.bridge.templates.media_player import MediaPlayerTemplate

        t = MediaPlayerTemplate()
        entities = [
            HAEntity(
                entity_id="media_player.speaker",
                state="playing",
                domain="media_player",
                attributes={"friendly_name": "Speaker", "volume_level": 0.5},
            ),
        ]
        items = t.build_items(entities)
        aliases = [i.alias for i in items]
        assert "MEDIA_PLAYER_SPEAKER" in aliases
        assert "MEDIA_PLAYER_SPEAKER_VOL" in aliases
        assert "MEDIA_PLAYER_SPEAKER_CMD" in aliases

    def test_8_service_writes(self):
        from ddf_toolkit.bridge.templates.media_player import MediaPlayerTemplate

        t = MediaPlayerTemplate()
        writes = t.build_writes(
            [HAEntity(entity_id="media_player.x", state="idle", domain="media_player")], []
        )
        assert len(writes) == 9  # GETSTATES + 8 services


class TestVacuumTemplate:
    def test_build_items(self):
        from ddf_toolkit.bridge.templates.vacuum import VacuumTemplate

        t = VacuumTemplate()
        entities = [
            HAEntity(
                entity_id="vacuum.robot",
                state="docked",
                domain="vacuum",
                attributes={"friendly_name": "Robot", "battery_level": 85},
            ),
        ]
        items = t.build_items(entities)
        aliases = [i.alias for i in items]
        assert "VACUUM_ROBOT" in aliases
        assert "VACUUM_ROBOT_BATTERY" in aliases
        assert "VACUUM_ROBOT_CMD" in aliases

    def test_build_writes(self):
        from ddf_toolkit.bridge.templates.vacuum import VacuumTemplate

        t = VacuumTemplate()
        writes = t.build_writes(
            [HAEntity(entity_id="vacuum.x", state="docked", domain="vacuum")], []
        )
        aliases = [w.alias for w in writes]
        assert "SVC_VAC_START" in aliases
        assert "SVC_VAC_RETURN" in aliases


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
