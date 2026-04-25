"""Domain template registry for HA → DDF mapping."""

from __future__ import annotations

from ddf_toolkit.bridge.templates.base import DomainTemplate
from ddf_toolkit.bridge.templates.binary_sensor import BinarySensorTemplate
from ddf_toolkit.bridge.templates.cover import CoverTemplate
from ddf_toolkit.bridge.templates.fan import FanTemplate
from ddf_toolkit.bridge.templates.light import LightTemplate
from ddf_toolkit.bridge.templates.lock import LockTemplate
from ddf_toolkit.bridge.templates.sensor import SensorTemplate
from ddf_toolkit.bridge.templates.switch import SwitchTemplate

TEMPLATES: dict[str, DomainTemplate] = {
    "switch": SwitchTemplate(),
    "sensor": SensorTemplate(),
    "binary_sensor": BinarySensorTemplate(),
    "lock": LockTemplate(),
    "light": LightTemplate(),
    "cover": CoverTemplate(),
    "fan": FanTemplate(),
}


def get_template(domain: str) -> DomainTemplate | None:
    return TEMPLATES.get(domain)


def supported_domains() -> list[str]:
    return list(TEMPLATES.keys())
