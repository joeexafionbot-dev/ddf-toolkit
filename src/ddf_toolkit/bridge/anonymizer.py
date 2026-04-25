"""Snapshot anonymizer — strip PII from HA snapshots before committing.

Rules (per Sprint 2 Amendments §7 + §10):
- Replace entity_ids with deterministic pseudonyms (per-snapshot seed)
- Strip device names, areas, friendly names
- Preserve domain, manufacturer, model, supported_features
- Preserve sensor values within reasonable bounds
- --verify mode checks all strings against an allowlist
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

# Allowlist: strings that are safe to appear in anonymized snapshots
SAFE_PATTERNS = [
    r"^(on|off|locked|unlocked|locking|unlocking|jammed)$",
    r"^(heat|cool|auto|heat_cool|dry|fan_only|off)$",
    r"^(open|closed|opening|closing)$",
    r"^(playing|paused|idle|standby|docked|cleaning|returning|error)$",
    r"^(auto|low|medium|high|standard|turbo|quiet)$",
    r"^(temperature|humidity|motion|door|window|smoke|gas|battery)$",
    r"^\d+(\.\d+)?$",  # numbers
    r"^[°%]",  # units
    r"^(°C|°F|%|W|kW|Wh|kWh|V|A|Hz|lx|m/s|ppm|Pa|s|min|h)$",
    r"^(true|false)$",
    r"^$",  # empty strings
    # HA service names and metadata
    r"^(turn_on|turn_off|toggle|lock|unlock|start|stop|return_to_base)$",
    r"^(set_temperature|set_hvac_mode|set_fan_mode|set_percentage)$",
    r"^(media_play|media_pause|media_stop|media_next_track|media_previous_track)$",
    r"^(volume_set|volume_up|volume_down|open_cover|close_cover|stop_cover)$",
    r"^(entity_id|description|service|fields|brightness|color_temp)$",
    r"^Entity ID$",
    r"^Brightness 0-255$",
    # Version strings and ISO timestamps
    r"^\d{4}\.\d+\.\d+$",  # HA version: 2026.1.4
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}",  # ISO8601 timestamps
    # Pseudonyms from anonymizer
    r"^(switch|light|sensor|binary_sensor|climate|cover|lock|fan|media_player|vacuum)\.",
    # Device metadata (manufacturer/model preserved by design)
    r"^Device [0-9a-f]+$",
    # Known safe manufacturer/model names (add as needed)
    r"^(Sonoff|Signify|Aqara|Tado|Somfy|Nuki|Generic|Sonos|Roborock)$",
    r"^(Basic R3|BSB002|RTCGQ11LM|RU01|TaHoma|3\.0 Pro|Ceiling Fan|One|S7)$",
]

_SAFE_COMPILED = [re.compile(p) for p in SAFE_PATTERNS]


def anonymize_snapshot(
    data: dict[str, Any],
    seed: str = "ddf-toolkit",
) -> dict[str, Any]:
    """Anonymize an HA snapshot. Per-snapshot deterministic pseudonyms."""
    result = dict(data)
    result["entities"] = [_anonymize_entity(e, seed) for e in data.get("entities", [])]
    result["devices"] = [_anonymize_device(d, seed) for d in data.get("devices", [])]

    # Strip config location
    if "config" in result:
        cfg = dict(result["config"])
        cfg["location_name"] = "Anonymized Home"
        cfg.pop("latitude", None)
        cfg.pop("longitude", None)
        result["config"] = cfg

    return result


def _pseudonym(value: str, seed: str, prefix: str = "") -> str:
    """Generate a deterministic pseudonym from a value."""
    h = hashlib.sha256(f"{seed}:{value}".encode()).hexdigest()[:8]
    if prefix:
        return f"{prefix}_{h}"
    return h


def _anonymize_entity(entity: dict[str, Any], seed: str) -> dict[str, Any]:
    """Anonymize a single entity."""
    result = dict(entity)
    eid = entity.get("entity_id", "")
    domain = eid.split(".")[0] if "." in eid else ""

    # Pseudonymize entity_id: light.living_room → light.location_a1b2c3d4
    result["entity_id"] = f"{domain}.location_{_pseudonym(eid, seed)}"

    # Strip friendly_name, replace with pseudonym
    attrs = dict(entity.get("attributes", {}))
    if "friendly_name" in attrs:
        attrs["friendly_name"] = f"Device {_pseudonym(eid, seed, 'dev')}"

    # Preserve safe attributes, strip others
    safe_attr_keys = {
        "supported_features",
        "device_class",
        "unit_of_measurement",
        "hvac_modes",
        "fan_modes",
        "fan_mode",
        "temperature",
        "current_temperature",
        "brightness",
        "color_temp",
        "current_position",
        "percentage",
        "oscillating",
        "volume_level",
        "battery_level",
        "fan_speed",
    }
    stripped_attrs = {}
    for k, v in attrs.items():
        if k in safe_attr_keys or k == "friendly_name":
            stripped_attrs[k] = v

    result["attributes"] = stripped_attrs

    # Pseudonymize device_id
    if "device_id" in result and result["device_id"]:
        result["device_id"] = _pseudonym(result["device_id"], seed, "dev")

    return result


def _anonymize_device(device: dict[str, Any], seed: str) -> dict[str, Any]:
    """Anonymize a single device."""
    result = dict(device)
    result["id"] = _pseudonym(device.get("id", ""), seed, "dev")
    result["name"] = f"Device {_pseudonym(device.get('id', ''), seed)}"

    # Preserve manufacturer and model (needed for grouping)
    # Strip area
    result["area"] = f"area_{_pseudonym(device.get('area', ''), seed)}"

    return result


def verify_anonymized(data: dict[str, Any]) -> list[str]:
    """Check all string values against the allowlist. Returns list of violations."""
    violations: list[str] = []
    _walk_verify(data, "", violations)
    return violations


def _walk_verify(obj: Any, path: str, violations: list[str]) -> None:
    """Recursively check all string values."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            _walk_verify(v, f"{path}.{k}", violations)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _walk_verify(v, f"{path}[{i}]", violations)
    elif isinstance(obj, str) and not _is_safe_string(obj):
        violations.append(f"{path}: {obj!r}")


def _is_safe_string(value: str) -> bool:
    """Check if a string value is safe (matches allowlist)."""
    # Short strings and known patterns
    if len(value) <= 3:
        return True
    for pattern in _SAFE_COMPILED:
        if pattern.match(value):
            return True
    # Pseudonyms generated by us (hex strings)
    if re.match(r"^(location_|dev_|area_|Device dev_)[0-9a-f]+$", value):
        return True
    # Schema metadata
    return value in ("ddf-toolkit synthetic", "Anonymized Home")


def anonymize_file(input_path: Path, output_path: Path, seed: str = "ddf-toolkit") -> list[str]:
    """Anonymize a snapshot file. Returns verification violations (should be empty)."""
    data = json.loads(input_path.read_text(encoding="utf-8"))
    anon = anonymize_snapshot(data, seed=seed)

    # Verify
    violations = verify_anonymized(anon)

    output_path.write_text(json.dumps(anon, indent=2, ensure_ascii=False), encoding="utf-8")
    return violations
