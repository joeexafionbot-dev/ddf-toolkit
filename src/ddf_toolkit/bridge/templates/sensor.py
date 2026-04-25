"""Sensor domain template — read-only numeric values.

HA sensor entities have: numeric state, unit_of_measurement. No services.
"""

from __future__ import annotations

from ddf_toolkit.bridge.models import HAEntity, HAService
from ddf_toolkit.bridge.templates.base import DomainTemplate
from ddf_toolkit.bridge.templates.common import (
    deduplicate_aliases,
    entity_alias,
    getstates_write,
)
from ddf_toolkit.parser.ast import Item, WriteCommand


class SensorTemplate(DomainTemplate):
    domain = "sensor"

    def can_handle(self, entity: HAEntity) -> bool:
        return entity.domain == "sensor"

    def build_items(self, entities: list[HAEntity]) -> list[Item]:
        items: list[Item] = []
        seen: set[str] = set()
        for idx, entity in enumerate(entities):
            alias = deduplicate_aliases(entity_alias(entity.entity_id), seen)
            seen.add(alias)
            items.append(
                Item(
                    alias=alias,
                    name=entity.friendly_name,
                    id=idx * 10,
                    unit=entity.unit or None,
                    rformula=(
                        f"IF GETSTATES.HTTP_CODE == 200 THEN\n"
                        f"    X.{alias} := GETSTATES.VALUE.{entity.entity_id}.state;\n"
                        f"ENDIF;"
                    ),
                    polling=5000,
                )
            )
        return items

    def build_writes(
        self, entities: list[HAEntity], services: list[HAService]
    ) -> list[WriteCommand]:
        return [getstates_write()]
