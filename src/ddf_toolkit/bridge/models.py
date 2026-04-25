"""Normalized data models for Home Assistant entities and devices."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class HADevice:
    """A physical device registered in Home Assistant."""

    id: str
    name: str
    manufacturer: str = ""
    model: str = ""
    area: str = ""
    sw_version: str = ""


@dataclass
class HAEntity:
    """A single Home Assistant entity (state + attributes)."""

    entity_id: str
    state: str
    domain: str
    attributes: dict[str, Any] = field(default_factory=dict)
    device_id: str | None = None

    @property
    def friendly_name(self) -> str:
        return self.attributes.get("friendly_name", self.entity_id)

    @property
    def supported_features(self) -> int:
        return int(self.attributes.get("supported_features", 0))

    @property
    def unit(self) -> str:
        return self.attributes.get("unit_of_measurement", "")


@dataclass
class HAService:
    """A Home Assistant service definition."""

    domain: str
    service: str
    fields: dict[str, Any] = field(default_factory=dict)


@dataclass
class HAConfig:
    """Home Assistant instance configuration."""

    version: str = ""
    location_name: str = ""
    latitude: float = 0.0
    longitude: float = 0.0


@dataclass
class HASnapshot:
    """Complete HA state snapshot."""

    schema_version: int = 1
    ha_version: str = ""
    captured_at: str = ""
    entities: list[HAEntity] = field(default_factory=list)
    devices: list[HADevice] = field(default_factory=list)
    services: dict[str, list[HAService]] = field(default_factory=dict)
    config: HAConfig = field(default_factory=HAConfig)
