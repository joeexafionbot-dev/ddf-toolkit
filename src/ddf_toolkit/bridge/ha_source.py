"""HA Source Adapter — load entities from live HA or snapshot file.

Two backends: HALiveSource (REST API) and HASnapshotSource (JSON file).
Both produce the same normalized HASnapshot model.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol

from ddf_toolkit.bridge.models import (
    HAConfig,
    HADevice,
    HAEntity,
    HAService,
    HASnapshot,
)


class HASourceError(Exception):
    pass


class HASource(Protocol):
    """Protocol for HA data sources."""

    def load(self) -> HASnapshot: ...


class HASnapshotSource:
    """Load a frozen JSON snapshot from disk."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> HASnapshot:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            msg = f"Cannot load snapshot {self.path}: {e}"
            raise HASourceError(msg) from e

        entities = [
            HAEntity(
                entity_id=e["entity_id"],
                state=e.get("state", ""),
                domain=e["entity_id"].split(".")[0],
                attributes=e.get("attributes", {}),
                device_id=e.get("device_id"),
            )
            for e in raw.get("entities", [])
        ]

        devices = [
            HADevice(
                id=d["id"],
                name=d.get("name", ""),
                manufacturer=d.get("manufacturer", ""),
                model=d.get("model", ""),
                area=d.get("area", ""),
                sw_version=d.get("sw_version", ""),
            )
            for d in raw.get("devices", [])
        ]

        services: dict[str, list[HAService]] = {}
        for domain, svc_list in raw.get("services", {}).items():
            services[domain] = [
                HAService(
                    domain=domain,
                    service=s.get("service", s.get("name", "")),
                    fields=s.get("fields", {}),
                )
                for s in svc_list
            ]

        config_raw = raw.get("config", {})
        config = HAConfig(
            version=config_raw.get("version", raw.get("ha_version", "")),
            location_name=config_raw.get("location_name", ""),
        )

        return HASnapshot(
            schema_version=raw.get("schema_version", 1),
            ha_version=raw.get("ha_version", ""),
            captured_at=raw.get("captured_at", ""),
            entities=entities,
            devices=devices,
            services=services,
            config=config,
        )


class HALiveSource:
    """Load from a live HA instance via REST API."""

    def __init__(self, base_url: str, token: str, timeout: int = 10) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout

    def load(self) -> HASnapshot:
        try:
            import httpx  # type: ignore[import-not-found]
        except ImportError as e:
            msg = "httpx is required for live HA source: pip install httpx"
            raise HASourceError(msg) from e

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

        try:
            client = httpx.Client(timeout=self.timeout)

            # Load states
            resp = client.get(f"{self.base_url}/api/states", headers=headers)
            resp.raise_for_status()
            states_raw = resp.json()

            # Load config
            resp = client.get(f"{self.base_url}/api/config", headers=headers)
            resp.raise_for_status()
            config_raw = resp.json()

            client.close()
        except Exception as e:
            msg = f"HA API error: {e}"
            raise HASourceError(msg) from e

        entities = [
            HAEntity(
                entity_id=s["entity_id"],
                state=s.get("state", ""),
                domain=s["entity_id"].split(".")[0],
                attributes=s.get("attributes", {}),
            )
            for s in states_raw
        ]

        config = HAConfig(
            version=config_raw.get("version", ""),
            location_name=config_raw.get("location_name", ""),
        )

        return HASnapshot(
            ha_version=config.version,
            entities=entities,
            config=config,
        )
