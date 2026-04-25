"""Switch domain template — the simplest HA → DDF mapping.

HA switch entities have: on/off state, turn_on/turn_off/toggle services.
This is the pattern prototype — all other templates follow this structure.
See docs/bridge.md for the canonical pattern documentation.
"""

from __future__ import annotations

from ddf_toolkit.bridge.models import HAEntity, HAService
from ddf_toolkit.bridge.templates.base import DomainTemplate
from ddf_toolkit.bridge.templates.common import (
    deduplicate_aliases,
    entity_alias,
    getstates_write,
    service_response_formula,
)
from ddf_toolkit.parser.ast import Item, WriteCommand


class SwitchTemplate(DomainTemplate):
    domain = "switch"

    def can_handle(self, entity: HAEntity) -> bool:
        return entity.domain == "switch"

    def build_items(self, entities: list[HAEntity]) -> list[Item]:
        items: list[Item] = []
        seen_aliases: set[str] = set()

        for idx, entity in enumerate(entities):
            alias = deduplicate_aliases(entity_alias(entity.entity_id), seen_aliases)
            seen_aliases.add(alias)

            # State item (read-only, polled from HA)
            items.append(
                Item(
                    alias=alias,
                    name=entity.friendly_name,
                    id=idx * 10,
                    unit=None,
                    rformula=_read_formula(entity, alias),
                    polling=5000,
                )
            )
            # Command item (write, triggers service call)
            cmd_alias = deduplicate_aliases(f"{alias}_CMD", seen_aliases)
            seen_aliases.add(cmd_alias)
            items.append(
                Item(
                    alias=cmd_alias,
                    name=f"{entity.friendly_name} Command",
                    id=idx * 10 + 1,
                    wformula=_write_formula(entity, alias),
                )
            )
        return items

    def build_writes(
        self, entities: list[HAEntity], services: list[HAService]
    ) -> list[WriteCommand]:
        writes: list[WriteCommand] = []
        writes.append(getstates_write())

        # Service calls: turn_on, turn_off
        for service_name in ["turn_on", "turn_off"]:
            writes.append(_service_write("switch", service_name))

        return writes


def _read_formula(entity: HAEntity, alias: str) -> str:
    """Generate RFORMULA for reading entity state from GETSTATES response."""
    eid = entity.entity_id
    return (
        f"IF GETSTATES.HTTP_CODE == 200 THEN\n    X.{alias} := GETSTATES.VALUE.{eid}.state;\nENDIF;"
    )


def _write_formula(entity: HAEntity, alias: str) -> str:
    """Generate WFORMULA for triggering service call on command change."""
    return (
        f"IF X.{alias}_CMD == 1 THEN\n"
        f"    SVC_TURN_ON.F := 1;\n"
        f"ELSE IF X.{alias}_CMD == 2 THEN\n"
        f"    SVC_TURN_OFF.F := 1;\n"
        f"ENDIF;\n"
        f"X.{alias}_CMD := 0;"
    )


def _service_write(domain: str, service: str) -> WriteCommand:
    """Build a standard HA service call write."""
    from ddf_toolkit.parser.ast import ArgsDef

    alias = f"SVC_{service.upper()}"
    return WriteCommand(
        alias=alias,
        method="POST",
        url=None,
        datatype="JSON",
        formula=service_response_formula(alias),
        args=[
            ArgsDef(
                method=None,
                alias=alias,
                type="url",
                name=f"/api/services/{domain}/{service}",
                value="",
            ),
            ArgsDef(
                method=None,
                alias=alias,
                type="header",
                name="Authorization",
                value="",
                item="$.CONFIG.1",
                format="Bearer %s",
            ),
            ArgsDef(
                method=None,
                alias=alias,
                type="header",
                name="Content-Type",
                value="application/json",
            ),
        ],
    )
