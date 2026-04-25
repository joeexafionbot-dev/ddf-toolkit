"""Light domain template — on/off, brightness, color_temp, optional RGB.

HA light: state (on/off), brightness (0-255), color_temp (mireds),
rgb_color ([r,g,b]). Services: turn_on (with optional params), turn_off, toggle.
Complexity: supported_features bitmask determines which attributes exist.
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
from ddf_toolkit.parser.ast import ArgsDef, Item, WriteCommand

# HA light supported_features bitmask
SUPPORT_BRIGHTNESS = 1
SUPPORT_COLOR_TEMP = 2
SUPPORT_COLOR = 16


class LightTemplate(DomainTemplate):
    domain = "light"

    def can_handle(self, entity: HAEntity) -> bool:
        return entity.domain == "light"

    def build_items(self, entities: list[HAEntity]) -> list[Item]:
        items: list[Item] = []
        seen: set[str] = set()

        for idx, entity in enumerate(entities):
            alias = deduplicate_aliases(entity_alias(entity.entity_id), seen)
            seen.add(alias)
            base_id = idx * 10
            features = entity.supported_features

            # State item (on/off)
            items.append(
                Item(
                    alias=alias,
                    name=entity.friendly_name,
                    id=base_id,
                    rformula=_state_rformula(entity, alias),
                    polling=5000,
                )
            )

            # Brightness (if supported)
            if features & SUPPORT_BRIGHTNESS:
                br_alias = deduplicate_aliases(f"{alias}_BRIGHTNESS", seen)
                seen.add(br_alias)
                items.append(
                    Item(
                        alias=br_alias,
                        name=f"{entity.friendly_name} Brightness",
                        id=base_id + 1,
                        unit="0-255",
                        rformula=(
                            f"IF GETSTATES.HTTP_CODE == 200 THEN\n"
                            f"    X.{br_alias} := GETSTATES.VALUE.{entity.entity_id}.attributes.brightness;\n"
                            f"ENDIF;"
                        ),
                        polling=5000,
                    )
                )

            # Color temp (if supported)
            if features & SUPPORT_COLOR_TEMP:
                ct_alias = deduplicate_aliases(f"{alias}_COLOR_TEMP", seen)
                seen.add(ct_alias)
                items.append(
                    Item(
                        alias=ct_alias,
                        name=f"{entity.friendly_name} Color Temp",
                        id=base_id + 2,
                        unit="mireds",
                        rformula=(
                            f"IF GETSTATES.HTTP_CODE == 200 THEN\n"
                            f"    X.{ct_alias} := GETSTATES.VALUE.{entity.entity_id}.attributes.color_temp;\n"
                            f"ENDIF;"
                        ),
                        polling=5000,
                    )
                )

            # Command item (turn_on/turn_off)
            cmd_alias = deduplicate_aliases(f"{alias}_CMD", seen)
            seen.add(cmd_alias)
            items.append(
                Item(
                    alias=cmd_alias,
                    name=f"{entity.friendly_name} Command",
                    id=base_id + 5,
                    wformula=(
                        f"IF X.{cmd_alias} == 1 THEN\n"
                        f"    SVC_LIGHT_TURN_ON.F := 1;\n"
                        f"ELSE IF X.{cmd_alias} == 2 THEN\n"
                        f"    SVC_LIGHT_TURN_OFF.F := 1;\n"
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

        for svc_name in ["turn_on", "turn_off"]:
            alias = f"SVC_LIGHT_{svc_name.upper()}"
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
                            name=f"/api/services/light/{svc_name}",
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


def _state_rformula(entity: HAEntity, alias: str) -> str:
    """Generate state RFORMULA: on → 1, off → 0."""
    return (
        f"IF GETSTATES.HTTP_CODE == 200 THEN\n"
        f"    IF ISEQUAL(GETSTATES.VALUE.{entity.entity_id}.state, 'on') THEN\n"
        f"        X.{alias} := 1;\n"
        f"    ELSE\n"
        f"        X.{alias} := 0;\n"
        f"    ENDIF;\n"
        f"ENDIF;"
    )
