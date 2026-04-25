"""Switch domain template — the simplest HA → DDF mapping.

HA switch entities have: on/off state, turn_on/turn_off/toggle services.
This is the pattern prototype — all other templates follow this structure.
"""

from __future__ import annotations

from ddf_toolkit.bridge.models import HAEntity, HAService
from ddf_toolkit.bridge.templates.base import DomainTemplate
from ddf_toolkit.parser.ast import ArgsDef, Item, WriteCommand


def _entity_alias(entity_id: str) -> str:
    """Convert HA entity_id to DDF-style alias: light.living_room → LIGHT_LIVING_ROOM."""
    return entity_id.replace(".", "_").upper()


class SwitchTemplate(DomainTemplate):
    domain = "switch"

    def can_handle(self, entity: HAEntity) -> bool:
        return entity.domain == "switch"

    def build_items(self, entities: list[HAEntity]) -> list[Item]:
        items: list[Item] = []
        for idx, entity in enumerate(entities):
            alias = _entity_alias(entity.entity_id)
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
            items.append(
                Item(
                    alias=f"{alias}_CMD",
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

        # GETSTATES — poll all entity states
        writes.append(
            WriteCommand(
                alias="GETSTATES",
                method="GET",
                url=None,
                datatype="JSON",
                formula=_getstates_formula(entities),
                args=[
                    ArgsDef(
                        method=None,
                        alias="GETSTATES",
                        type="url",
                        name="/api/states",
                        value="",
                    ),
                    ArgsDef(
                        method=None,
                        alias="GETSTATES",
                        type="header",
                        name="Authorization",
                        value="",
                        item="$.CONFIG.1",
                        format="Bearer %s",
                    ),
                ],
            )
        )

        # Service calls: turn_on, turn_off
        for service_name in ["turn_on", "turn_off"]:
            alias = f"SVC_{service_name.upper()}"
            writes.append(
                WriteCommand(
                    alias=alias,
                    method="POST",
                    url=None,
                    datatype="JSON",
                    formula=_service_response_formula(alias),
                    args=[
                        ArgsDef(
                            method=None,
                            alias=alias,
                            type="url",
                            name=f"/api/services/switch/{service_name}",
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
            )

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


def _getstates_formula(entities: list[HAEntity]) -> str:
    """Generate response formula for GETSTATES write."""
    lines = ["IF GETSTATES.HTTP_CODE == 200 THEN"]
    lines.append("    X.200 := 1;")
    lines.append("ELSE")
    lines.append("    X.200 := 0;")
    lines.append("ENDIF;")
    lines.append("GETSTATES.F := 0;")
    return "\n".join(lines)


def _service_response_formula(alias: str) -> str:
    """Generate response formula for a service call."""
    return (
        f"IF {alias}.HTTP_CODE == 200 THEN\n"
        f"    DEBUG('Service call OK');\n"
        f"ELSE\n"
        f"    DEBUG({alias}.HTTP_DATA);\n"
        f"ENDIF;\n"
        f"{alias}.F := 0;"
    )
