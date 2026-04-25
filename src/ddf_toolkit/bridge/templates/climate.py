"""Climate domain template — HVAC with modes, setpoints, fan control.

HA climate: current_temperature, temperature (setpoint), hvac_mode,
fan_mode. Services: set_temperature, set_hvac_mode, set_fan_mode.
"""

from __future__ import annotations

from ddf_toolkit.bridge.models import HAEntity, HAService
from ddf_toolkit.bridge.templates.base import DomainTemplate
from ddf_toolkit.bridge.templates.common import (
    deduplicate_aliases,
    entity_alias,
    enum_attr_rformula,
    enum_rformula,
    getstates_write,
    service_response_formula,
)
from ddf_toolkit.parser.ast import ArgsDef, Item, WriteCommand


class ClimateTemplate(DomainTemplate):
    domain = "climate"

    def can_handle(self, entity: HAEntity) -> bool:
        return entity.domain == "climate"

    def build_items(self, entities: list[HAEntity]) -> list[Item]:
        items: list[Item] = []
        seen: set[str] = set()

        for idx, entity in enumerate(entities):
            alias = deduplicate_aliases(entity_alias(entity.entity_id), seen)
            seen.add(alias)
            base_id = idx * 10

            # Current temperature
            temp_alias = deduplicate_aliases(f"{alias}_TEMP", seen)
            seen.add(temp_alias)
            items.append(
                Item(
                    alias=temp_alias,
                    name=f"{entity.friendly_name} Temperature",
                    id=base_id,
                    unit="°C",
                    rformula=(
                        f"IF GETSTATES.HTTP_CODE == 200 THEN\n"
                        f"    X.{temp_alias} := GETSTATES.VALUE.{entity.entity_id}.attributes.current_temperature;\n"
                        f"ENDIF;"
                    ),
                    polling=5000,
                )
            )

            # Target temperature (setpoint)
            setpoint_alias = deduplicate_aliases(f"{alias}_SETPOINT", seen)
            seen.add(setpoint_alias)
            items.append(
                Item(
                    alias=setpoint_alias,
                    name=f"{entity.friendly_name} Setpoint",
                    id=base_id + 1,
                    unit="°C",
                    rformula=(
                        f"IF GETSTATES.HTTP_CODE == 200 THEN\n"
                        f"    X.{setpoint_alias} := GETSTATES.VALUE.{entity.entity_id}.attributes.temperature;\n"
                        f"ENDIF;"
                    ),
                    wformula=("SVC_SET_TEMPERATURE.F := 1;"),
                    polling=5000,
                )
            )

            # HVAC mode
            mode_alias = deduplicate_aliases(f"{alias}_MODE", seen)
            seen.add(mode_alias)
            items.append(
                Item(
                    alias=mode_alias,
                    name=f"{entity.friendly_name} Mode",
                    id=base_id + 2,
                    rformula=enum_rformula(
                        entity.entity_id,
                        mode_alias,
                        ["off", "heat", "cool", "auto", "heat_cool", "dry", "fan_only"],
                    ),
                    polling=5000,
                )
            )

            # Fan mode (if supported)
            fan_modes = entity.attributes.get("fan_modes")
            if fan_modes:
                fan_alias = deduplicate_aliases(f"{alias}_FAN", seen)
                seen.add(fan_alias)
                items.append(
                    Item(
                        alias=fan_alias,
                        name=f"{entity.friendly_name} Fan Mode",
                        id=base_id + 3,
                        rformula=enum_attr_rformula(
                            entity.entity_id,
                            fan_alias,
                            "fan_mode",
                            fan_modes,
                        ),
                        polling=5000,
                    )
                )

        return items

    def build_writes(
        self, entities: list[HAEntity], services: list[HAService]
    ) -> list[WriteCommand]:
        writes = [getstates_write()]

        for svc_name in ["set_temperature", "set_hvac_mode", "set_fan_mode"]:
            alias = f"SVC_{svc_name.upper()}"
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
                            name=f"/api/services/climate/{svc_name}",
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
