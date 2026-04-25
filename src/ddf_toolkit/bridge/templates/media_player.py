"""Media player domain template — state, volume, source, transport controls.

HA media_player: state, volume_level, source, media_title.
Services (essential 8): media_play, media_pause, media_stop, media_next_track,
media_previous_track, volume_set, volume_up, volume_down.
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

# Essential services (PRD says 8, we cover these)
MEDIA_SERVICES = [
    "media_play",
    "media_pause",
    "media_stop",
    "media_next_track",
    "media_previous_track",
    "volume_set",
    "volume_up",
    "volume_down",
]


class MediaPlayerTemplate(DomainTemplate):
    domain = "media_player"

    def can_handle(self, entity: HAEntity) -> bool:
        return entity.domain == "media_player"

    def build_items(self, entities: list[HAEntity]) -> list[Item]:
        items: list[Item] = []
        seen: set[str] = set()

        for idx, entity in enumerate(entities):
            alias = deduplicate_aliases(entity_alias(entity.entity_id), seen)
            seen.add(alias)
            base_id = idx * 10

            # State (playing/paused/idle/off)
            items.append(
                Item(
                    alias=alias,
                    name=entity.friendly_name,
                    id=base_id,
                    rformula=(
                        f"IF GETSTATES.HTTP_CODE == 200 THEN\n"
                        f"    X.{alias} := GETSTATES.VALUE.{entity.entity_id}.state;\n"
                        f"ENDIF;"
                    ),
                    polling=5000,
                )
            )

            # Volume
            vol_alias = deduplicate_aliases(f"{alias}_VOL", seen)
            seen.add(vol_alias)
            items.append(
                Item(
                    alias=vol_alias,
                    name=f"{entity.friendly_name} Volume",
                    id=base_id + 1,
                    unit="0-1",
                    rformula=(
                        f"IF GETSTATES.HTTP_CODE == 200 THEN\n"
                        f"    X.{vol_alias} := GETSTATES.VALUE.{entity.entity_id}.attributes.volume_level;\n"
                        f"ENDIF;"
                    ),
                    polling=5000,
                )
            )

            # Source
            src_alias = deduplicate_aliases(f"{alias}_SRC", seen)
            seen.add(src_alias)
            items.append(
                Item(
                    alias=src_alias,
                    name=f"{entity.friendly_name} Source",
                    id=base_id + 2,
                    rformula=(
                        f"IF GETSTATES.HTTP_CODE == 200 THEN\n"
                        f"    X.{src_alias} := GETSTATES.VALUE.{entity.entity_id}.attributes.source;\n"
                        f"ENDIF;"
                    ),
                    polling=5000,
                )
            )

            # Media title
            title_alias = deduplicate_aliases(f"{alias}_TITLE", seen)
            seen.add(title_alias)
            items.append(
                Item(
                    alias=title_alias,
                    name=f"{entity.friendly_name} Title",
                    id=base_id + 3,
                    rformula=(
                        f"IF GETSTATES.HTTP_CODE == 200 THEN\n"
                        f"    X.{title_alias} := GETSTATES.VALUE.{entity.entity_id}.attributes.media_title;\n"
                        f"ENDIF;"
                    ),
                    polling=5000,
                )
            )

            # Transport command
            cmd_alias = deduplicate_aliases(f"{alias}_CMD", seen)
            seen.add(cmd_alias)
            items.append(
                Item(
                    alias=cmd_alias,
                    name=f"{entity.friendly_name} Command",
                    id=base_id + 5,
                    wformula=(
                        f"IF X.{cmd_alias} == 1 THEN\n"
                        f"    SVC_MEDIA_PLAY.F := 1;\n"
                        f"ELSE IF X.{cmd_alias} == 2 THEN\n"
                        f"    SVC_MEDIA_PAUSE.F := 1;\n"
                        f"ELSE IF X.{cmd_alias} == 3 THEN\n"
                        f"    SVC_MEDIA_STOP.F := 1;\n"
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

        for svc_name in MEDIA_SERVICES:
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
                            name=f"/api/services/media_player/{svc_name}",
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
