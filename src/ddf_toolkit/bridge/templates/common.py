"""Common helpers shared across all domain templates.

These enforce the canonical patterns documented in docs/bridge.md.
"""

from __future__ import annotations

from ddf_toolkit.parser.ast import ArgsDef, WriteCommand


def entity_alias(entity_id: str) -> str:
    """Convert HA entity_id to DDF-style alias.

    light.living_room → LIGHT_LIVING_ROOM
    """
    return entity_id.replace(".", "_").replace(" ", "_").upper()


def deduplicate_aliases(alias: str, seen: set[str]) -> str:
    """Ensure alias is unique by appending a numeric suffix if needed."""
    if alias not in seen:
        return alias
    suffix = 2
    while f"{alias}_{suffix}" in seen:
        suffix += 1
    return f"{alias}_{suffix}"


def getstates_write() -> WriteCommand:
    """Standard GETSTATES write — polls GET /api/states.

    Every generated DDF has exactly one of these. See docs/bridge.md.
    """
    return WriteCommand(
        alias="GETSTATES",
        method="GET",
        url=None,
        datatype="JSON",
        formula=_getstates_formula(),
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


def service_response_formula(alias: str) -> str:
    """Standard error-handling formula for service call responses.

    Handles 200 (OK), 401 (token expired), and other errors.
    See docs/bridge.md Error Handling section.
    """
    return (
        f"IF {alias}.HTTP_CODE == 200 THEN\n"
        f"    X.200 := 1;\n"
        f"ELSE IF {alias}.HTTP_CODE == 401 THEN\n"
        f"    DEBUG('Token expired');\n"
        f"    X.201 := 0;\n"
        f"ELSE\n"
        f"    DEBUG({alias}.HTTP_DATA);\n"
        f"    X.200 := 0;\n"
        f"ENDIF;\n"
        f"{alias}.F := 0;"
    )


def enum_rformula(entity_id: str, alias: str, values: list[str]) -> str:
    """Generate RFORMULA for closed-domain enum mapping.

    Maps HA string states to integer values for *OBJECT UI dropdown.
    See docs/bridge.md String-vs-Enum Mapping Pattern.
    """
    lines = ["IF GETSTATES.HTTP_CODE == 200 THEN"]
    for idx, value in enumerate(values):
        prefix = "    IF" if idx == 0 else "    ELSE IF"
        lines.append(f"{prefix} ISEQUAL(GETSTATES.VALUE.{entity_id}.state, '{value}') THEN")
        lines.append(f"        X.{alias} := {idx};")
    lines.append("    ENDIF;")
    lines.append("ENDIF;")
    return "\n".join(lines)


def enum_attr_rformula(entity_id: str, alias: str, attr_name: str, values: list[str]) -> str:
    """Generate RFORMULA for closed-domain enum on an attribute (not state)."""
    lines = ["IF GETSTATES.HTTP_CODE == 200 THEN"]
    for idx, value in enumerate(values):
        prefix = "    IF" if idx == 0 else "    ELSE IF"
        lines.append(
            f"{prefix} ISEQUAL(GETSTATES.VALUE.{entity_id}.attributes.{attr_name}, '{value}') THEN"
        )
        lines.append(f"        X.{alias} := {idx};")
    lines.append("    ENDIF;")
    lines.append("ENDIF;")
    return "\n".join(lines)


def _getstates_formula() -> str:
    """Standard response formula for GETSTATES poll."""
    return (
        "IF GETSTATES.HTTP_CODE == 200 THEN\n"
        "    X.200 := 1;\n"
        "ELSE IF GETSTATES.HTTP_CODE == 401 THEN\n"
        "    DEBUG('Token expired');\n"
        "    X.201 := 0;\n"
        "ELSE\n"
        "    DEBUG(GETSTATES.HTTP_DATA);\n"
        "    X.200 := 0;\n"
        "ENDIF;\n"
        "GETSTATES.F := 0;"
    )
