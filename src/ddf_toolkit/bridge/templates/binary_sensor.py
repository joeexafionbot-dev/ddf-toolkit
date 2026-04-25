"""Binary sensor domain template — read-only boolean state.

HA binary_sensor: on/off state, device_class (motion, door, etc.). No services.
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


class BinarySensorTemplate(DomainTemplate):
    domain = "binary_sensor"

    def can_handle(self, entity: HAEntity) -> bool:
        return entity.domain == "binary_sensor"

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
                    rformula=(
                        f"IF GETSTATES.HTTP_CODE == 200 THEN\n"
                        f"    IF ISEQUAL(GETSTATES.VALUE.{entity.entity_id}.state, 'on') THEN\n"
                        f"        X.{alias} := 1;\n"
                        f"    ELSE\n"
                        f"        X.{alias} := 0;\n"
                        f"    ENDIF;\n"
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
