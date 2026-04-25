"""Lock domain template — locked/unlocked state with lock/unlock services.

HA lock: locked/unlocked/locking/unlocking state. Services: lock, unlock.
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


class LockTemplate(DomainTemplate):
    domain = "lock"

    def can_handle(self, entity: HAEntity) -> bool:
        return entity.domain == "lock"

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
                        f"    IF ISEQUAL(GETSTATES.VALUE.{entity.entity_id}.state, 'locked') THEN\n"
                        f"        X.{alias} := 1;\n"
                        f"    ELSE\n"
                        f"        X.{alias} := 0;\n"
                        f"    ENDIF;\n"
                        f"ENDIF;"
                    ),
                    polling=5000,
                )
            )
            cmd_alias = deduplicate_aliases(f"{alias}_CMD", seen)
            seen.add(cmd_alias)
            items.append(
                Item(
                    alias=cmd_alias,
                    name=f"{entity.friendly_name} Command",
                    id=idx * 10 + 1,
                    wformula=(
                        f"IF X.{cmd_alias} == 1 THEN\n"
                        f"    SVC_LOCK.F := 1;\n"
                        f"ELSE IF X.{cmd_alias} == 2 THEN\n"
                        f"    SVC_UNLOCK.F := 1;\n"
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
        for svc_name in ["lock", "unlock"]:
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
                            name=f"/api/services/lock/{svc_name}",
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
