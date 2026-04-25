"""Cover domain template — position-based blinds/shutters.

HA cover: state (open/closed/opening/closing), current_position (0-100).
Services: open_cover, close_cover, set_cover_position, stop_cover.
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


class CoverTemplate(DomainTemplate):
    domain = "cover"

    def can_handle(self, entity: HAEntity) -> bool:
        return entity.domain == "cover"

    def build_items(self, entities: list[HAEntity]) -> list[Item]:
        items: list[Item] = []
        seen: set[str] = set()
        for idx, entity in enumerate(entities):
            alias = deduplicate_aliases(entity_alias(entity.entity_id), seen)
            seen.add(alias)
            base_id = idx * 10

            # State (open/closed)
            items.append(
                Item(
                    alias=alias,
                    name=entity.friendly_name,
                    id=base_id,
                    rformula=enum_rformula(
                        entity.entity_id,
                        alias,
                        ["closed", "open", "opening", "closing"],
                    ),
                    polling=5000,
                )
            )

            # Position
            pos_alias = deduplicate_aliases(f"{alias}_POS", seen)
            seen.add(pos_alias)
            items.append(
                Item(
                    alias=pos_alias,
                    name=f"{entity.friendly_name} Position",
                    id=base_id + 1,
                    unit="%",
                    rformula=(
                        f"IF GETSTATES.HTTP_CODE == 200 THEN\n"
                        f"    X.{pos_alias} := GETSTATES.VALUE.{entity.entity_id}.attributes.current_position;\n"
                        f"ENDIF;"
                    ),
                    polling=5000,
                )
            )

            # Command
            cmd_alias = deduplicate_aliases(f"{alias}_CMD", seen)
            seen.add(cmd_alias)
            items.append(
                Item(
                    alias=cmd_alias,
                    name=f"{entity.friendly_name} Command",
                    id=base_id + 2,
                    wformula=(
                        f"IF X.{cmd_alias} == 1 THEN\n"
                        f"    SVC_OPEN_COVER.F := 1;\n"
                        f"ELSE IF X.{cmd_alias} == 2 THEN\n"
                        f"    SVC_CLOSE_COVER.F := 1;\n"
                        f"ELSE IF X.{cmd_alias} == 3 THEN\n"
                        f"    SVC_STOP_COVER.F := 1;\n"
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
        for svc_name in ["open_cover", "close_cover", "stop_cover"]:
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
                            name=f"/api/services/cover/{svc_name}",
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
