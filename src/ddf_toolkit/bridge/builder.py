"""DDF Builder — compose template outputs into a complete DDF AST.

Takes integration group + template outputs and builds a full DDF with:
*GENERAL (both blocks), *CONFIG, *COMMAND, *WRITE, *ITEM, *GROUP, *OBJECT
"""

from __future__ import annotations

import hashlib

from ddf_toolkit.bridge.grouper import IntegrationGroup
from ddf_toolkit.bridge.models import HAEntity, HAService
from ddf_toolkit.bridge.templates import get_template
from ddf_toolkit.parser.ast import (
    DDF,
    CommandDef,
    ConfigField,
    GeneralMetadata,
    GeneralParams,
    Group,
    Item,
    WriteCommand,
)


def build_ddf(
    group: IntegrationGroup,
    services: dict[str, list[HAService]] | None = None,
) -> DDF:
    """Build a complete DDF from an integration group.

    Dispatches entities to their domain templates, collects outputs,
    composes into a full DDF AST.
    """
    services = services or {}

    # Collect items and writes from domain templates
    all_items: list[Item] = []
    all_writes: list[WriteCommand] = []
    domains_used: set[str] = set()

    # Group entities by domain
    by_domain: dict[str, list[HAEntity]] = {}
    for entity in group.entities:
        by_domain.setdefault(entity.domain, []).append(entity)

    for domain, entities in sorted(by_domain.items()):
        template = get_template(domain)
        if template is None:
            continue

        domain_services = services.get(domain, [])
        items = template.build_items(entities)
        writes = template.build_writes(entities, domain_services)

        all_items.extend(items)
        all_writes.extend(writes)
        domains_used.add(domain)

    # Add quality items (standard for all DDFs)
    quality_id = max((i.id for i in all_items), default=-1) + 1
    all_items.append(Item(alias="QUALITY", name="Data Quality", id=quality_id, default="1"))
    all_items.append(
        Item(alias="QUALITY_TOKEN", name="Token Quality", id=quality_id + 1, default="1")
    )

    # Build groups from domains
    groups = [
        Group(id=idx, alias=domain.upper(), name=domain.replace("_", " ").title())
        for idx, domain in enumerate(sorted(domains_used))
    ]

    # Build general metadata
    device_id = _generate_device_id(group.manufacturer, group.model)
    metadata = GeneralMetadata(
        device=group.model or "HA Device",
        manufacturer=group.manufacturer or "Home Assistant",
        type="HA-Bridge",
        protocol="REST-API (DDF)",
        model_nr="1",
        version_nr="1",
        id=device_id,
        min_control_version="V10000-01",
        timestamp="",
    )

    params = GeneralParams(
        connection="DOMAIN",
        authentification="PASSWORD",
        domain="",
        debugport=8500,
    )

    # Config fields: URL, Token, Polling
    config = [
        ConfigField(id=0, alias="HA_URL"),
        ConfigField(id=1, alias="HA_TOKEN"),
        ConfigField(id=2, alias="POLL_INTERVAL"),
    ]

    # Commands
    commands = [
        CommandDef(id=0, alias="REFRESH", formula="GETSTATES.F := 1;"),
    ]

    return DDF(
        signature=None,
        general_metadata=metadata,
        general_params=params,
        commands=commands,
        config=config,
        reads=[],
        writes=all_writes,
        items=all_items,
        groups=groups,
        objects=[],
        raw_source="",
    )


def _generate_device_id(manufacturer: str, model: str, schema_version: int = 1) -> str:
    """Generate deterministic device ID with 0xFA prefix for HA-Bridge DDFs.

    Format: 0x0DFA00<8-hex-hash>0100
    """
    seed = f"{manufacturer}|{model}|{schema_version}"
    h = hashlib.sha256(seed.encode()).hexdigest()[:8]
    return f"0x0DFA00{h}0100"
