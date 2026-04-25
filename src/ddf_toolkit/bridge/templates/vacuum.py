"""Vacuum domain template — state, battery, fan speed, basic controls.

HA vacuum: state (docked/cleaning/returning/error), battery_level,
fan_speed. Services: start, stop, return_to_base.
"""

from __future__ import annotations

from ddf_toolkit.bridge.models import HAEntity, HAService
from ddf_toolkit.bridge.templates.base import DomainTemplate
from ddf_toolkit.bridge.templates.common import (
    deduplicate_aliases,
    entity_alias,
    enum_rformula,
    getstates_write,
    service_response_formula,
)
from ddf_toolkit.parser.ast import ArgsDef, Item, WriteCommand


class VacuumTemplate(DomainTemplate):
    domain = "vacuum"

    def can_handle(self, entity: HAEntity) -> bool:
        return entity.domain == "vacuum"

    def build_items(self, entities: list[HAEntity]) -> list[Item]:
        items: list[Item] = []
        seen: set[str] = set()

        for idx, entity in enumerate(entities):
            alias = deduplicate_aliases(entity_alias(entity.entity_id), seen)
            seen.add(alias)
            base_id = idx * 10

            # State (docked/cleaning/returning/error)
            items.append(
                Item(
                    alias=alias,
                    name=entity.friendly_name,
                    id=base_id,
                    rformula=enum_rformula(
                        entity.entity_id,
                        alias,
                        ["docked", "cleaning", "returning", "paused", "idle", "error"],
                    ),
                    polling=5000,
                )
            )

            # Battery level
            bat_alias = deduplicate_aliases(f"{alias}_BATTERY", seen)
            seen.add(bat_alias)
            items.append(
                Item(
                    alias=bat_alias,
                    name=f"{entity.friendly_name} Battery",
                    id=base_id + 1,
                    unit="%",
                    rformula=(
                        f"IF GETSTATES.HTTP_CODE == 200 THEN\n"
                        f"    X.{bat_alias} := GETSTATES.VALUE.{entity.entity_id}.attributes.battery_level;\n"
                        f"ENDIF;"
                    ),
                    polling=10000,
                )
            )

            # Fan speed
            fan_alias = deduplicate_aliases(f"{alias}_FAN_SPEED", seen)
            seen.add(fan_alias)
            items.append(
                Item(
                    alias=fan_alias,
                    name=f"{entity.friendly_name} Fan Speed",
                    id=base_id + 2,
                    rformula=(
                        f"IF GETSTATES.HTTP_CODE == 200 THEN\n"
                        f"    X.{fan_alias} := GETSTATES.VALUE.{entity.entity_id}.attributes.fan_speed;\n"
                        f"ENDIF;"
                    ),
                    polling=10000,
                )
            )

            # Command
            cmd_alias = deduplicate_aliases(f"{alias}_CMD", seen)
            seen.add(cmd_alias)
            items.append(
                Item(
                    alias=cmd_alias,
                    name=f"{entity.friendly_name} Command",
                    id=base_id + 5,
                    wformula=(
                        f"IF X.{cmd_alias} == 1 THEN\n"
                        f"    SVC_VAC_START.F := 1;\n"
                        f"ELSE IF X.{cmd_alias} == 2 THEN\n"
                        f"    SVC_VAC_STOP.F := 1;\n"
                        f"ELSE IF X.{cmd_alias} == 3 THEN\n"
                        f"    SVC_VAC_RETURN.F := 1;\n"
                        f"ENDIF;\n"
                        f"X.{cmd_alias} := 0;"
                    ),
                )
            )

        return items

    def build_writes(
        self, entities: list[HAEntity], services: list[HAService]
    ) -> list[WriteCommand]:
        writes = [getstates_write()]

        svc_map = {"start": "VAC_START", "stop": "VAC_STOP", "return_to_base": "VAC_RETURN"}
        for svc_name, alias_suffix in svc_map.items():
            alias = f"SVC_{alias_suffix}"
            writes.append(
                WriteCommand(
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
                            name=f"/api/services/vacuum/{svc_name}",
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
