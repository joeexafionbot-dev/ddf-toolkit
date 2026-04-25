"""Domain template registry for HA → DDF mapping."""

from __future__ import annotations

from ddf_toolkit.bridge.templates.base import DomainTemplate
from ddf_toolkit.bridge.templates.binary_sensor import BinarySensorTemplate
from ddf_toolkit.bridge.templates.lock import LockTemplate
from ddf_toolkit.bridge.templates.sensor import SensorTemplate
from ddf_toolkit.bridge.templates.switch import SwitchTemplate

# Registry — add templates as they're implemented
TEMPLATES: dict[str, DomainTemplate] = {
    "switch": SwitchTemplate(),
    "sensor": SensorTemplate(),
    "binary_sensor": BinarySensorTemplate(),
    "lock": LockTemplate(),
}


def get_template(domain: str) -> DomainTemplate | None:
    """Get the template for a given HA domain."""
    return TEMPLATES.get(domain)


def supported_domains() -> list[str]:
    """List all supported HA domains."""
    return list(TEMPLATES.keys())
