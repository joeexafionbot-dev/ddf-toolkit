"""Integration Grouper — group HA entities into DDF-sized units.

Algorithm:
1. Group entities by (device.manufacturer, device.model)
2. Within group, split if >25 items (by area, then numeric)
3. Entities without devices → _unknown group
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from ddf_toolkit.bridge.models import HADevice, HAEntity, HASnapshot

MAX_ITEMS_PER_DDF = 25


@dataclass
class IntegrationGroup:
    """A group of entities that will become one DDF."""

    manufacturer: str
    model: str
    entities: list[HAEntity] = field(default_factory=list)
    device: HADevice | None = None

    @property
    def name(self) -> str:
        if self.manufacturer and self.model:
            return f"{self.manufacturer} {self.model}"
        if self.manufacturer:
            return self.manufacturer
        return "_unknown"

    @property
    def key(self) -> str:
        return f"{self.manufacturer}|{self.model}".lower()


def group_entities(snapshot: HASnapshot) -> list[IntegrationGroup]:
    """Group entities into DDF-sized integration groups."""
    device_map = {d.id: d for d in snapshot.devices}

    # Group by (manufacturer, model)
    raw_groups: dict[str, list[HAEntity]] = defaultdict(list)
    group_devices: dict[str, HADevice | None] = {}

    for entity in snapshot.entities:
        device = device_map.get(entity.device_id or "") if entity.device_id else None
        if device and device.manufacturer:
            key = f"{device.manufacturer}|{device.model}".lower()
            group_devices[key] = device
        else:
            key = "_unknown|"
            group_devices.setdefault(key, None)
        raw_groups[key].append(entity)

    # Split oversized groups
    result: list[IntegrationGroup] = []
    for key, entities in sorted(raw_groups.items()):
        manufacturer, model = key.split("|", 1)
        device = group_devices.get(key)

        if len(entities) <= MAX_ITEMS_PER_DDF:
            result.append(
                IntegrationGroup(
                    manufacturer=manufacturer,
                    model=model,
                    entities=entities,
                    device=device,
                )
            )
        else:
            # Split by area first
            by_area: dict[str, list[HAEntity]] = defaultdict(list)
            for e in entities:
                area = ""
                if e.device_id and e.device_id in device_map:
                    area = device_map[e.device_id].area
                by_area[area or "_noarea"].append(e)

            for area_name, area_entities in sorted(by_area.items()):
                # Further split if still too large
                for chunk_idx in range(0, len(area_entities), MAX_ITEMS_PER_DDF):
                    chunk = area_entities[chunk_idx : chunk_idx + MAX_ITEMS_PER_DDF]
                    suffix = f" ({area_name})" if len(by_area) > 1 else ""
                    if chunk_idx > 0:
                        suffix += f" Part {chunk_idx // MAX_ITEMS_PER_DDF + 1}"
                    result.append(
                        IntegrationGroup(
                            manufacturer=manufacturer,
                            model=model + suffix,
                            entities=chunk,
                            device=device,
                        )
                    )

    return result
