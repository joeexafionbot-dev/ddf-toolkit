"""DDF parser — converts lexed rows into a typed DDF AST."""

from __future__ import annotations

from pathlib import Path

from ddf_toolkit.parser.ast import (
    DDF,
    ArgsDef,
    CommandDef,
    ConfigField,
    GeneralMetadata,
    GeneralParams,
    Group,
    Item,
    ObjectDef,
    SignatureSection,
    WriteCommand,
)
from ddf_toolkit.parser.lexer import DDFRow, DDFSyntaxError, lex_ddf


def _cell(cells: list[str], index: int, default: str = "") -> str:
    """Safely get a cell value, stripped."""
    if index < len(cells):
        return cells[index].strip().strip('"')
    return default


def _int_or_none(value: str) -> int | None:
    value = value.strip()
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _float_or_none(value: str) -> float | None:
    value = value.strip()
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _parse_signature(rows: list[DDFRow]) -> SignatureSection | None:
    sig_rows = [r for r in rows if r.section == "*SIGNATURE"]
    if not sig_rows:
        return None

    fields: dict[str, str] = {}
    for row in sig_rows:
        key = _cell(row.cells, 1).upper()
        val = _cell(row.cells, 2)
        if key:
            fields[key] = val

    return SignatureSection(
        sign_algo=fields.get("SIGN_ALGO", ""),
        sign_date=fields.get("SIGN_DATE", ""),
        file_verdate=fields.get("FILE_VERDATE", ""),
        signature=fields.get("SIGNATURE", ""),
    )


def _parse_general(rows: list[DDFRow]) -> tuple[GeneralMetadata, GeneralParams]:
    gen_rows = [r for r in rows if r.section == "*GENERAL"]
    if not gen_rows:
        raise DDFSyntaxError("Missing *GENERAL section")

    # First pass: collect all key-value pairs
    fields: dict[str, str] = {}
    for row in gen_rows:
        key = _cell(row.cells, 1).upper()
        val = _cell(row.cells, 2)
        if key:
            fields[key] = val

    metadata = GeneralMetadata(
        device=fields.get("DEVICE", ""),
        manufacturer=fields.get("MANUFACTURER", ""),
        type=fields.get("TYPE", ""),
        protocol=fields.get("PROTOCOL", ""),
        model_nr=fields.get("MODEL_NR", ""),
        version_nr=fields.get("VERSION_NR", ""),
        id=fields.get("ID", ""),
        min_control_version=fields.get("MIN_CONTROL_VERSION", ""),
        timestamp=fields.get("TIMESTAMP", ""),
        version_info=fields.get("VERSION_INFO"),
        version_user=fields.get("VERSION_USER"),
        revision=fields.get("REVISION"),
    )

    # Extra params not part of metadata go into GeneralParams
    extra_keys = set(fields.keys()) - {
        "DEVICE",
        "MANUFACTURER",
        "TYPE",
        "PROTOCOL",
        "MODEL_NR",
        "VERSION_NR",
        "ID",
        "MIN_CONTROL_VERSION",
        "TIMESTAMP",
        "VERSION_INFO",
        "VERSION_USER",
        "REVISION",
        "CONNECTION",
        "AUTHENTIFICATION",
        "DOMAIN",
        "SLAVESMAX",
        "DEBUGPORT",
    }

    # For domain_alt: check if there's a secondary value in column 3+
    domain_row = next(
        (r for r in gen_rows if _cell(r.cells, 1).upper() == "DOMAIN"),
        None,
    )
    domain_alt = None
    if domain_row and len(domain_row.cells) > 3:
        alt = _cell(domain_row.cells, 3)
        if alt:
            domain_alt = alt

    params = GeneralParams(
        connection=fields.get("CONNECTION", ""),
        authentification=fields.get("AUTHENTIFICATION", ""),
        domain=fields.get("DOMAIN", ""),
        domain_alt=domain_alt,
        slavesmax=_int_or_none(fields.get("SLAVESMAX", "")),
        debugport=_int_or_none(fields.get("DEBUGPORT", "")),
        extra={k: fields[k] for k in extra_keys if fields[k]},
    )

    return metadata, params


def _parse_commands(rows: list[DDFRow]) -> list[CommandDef]:
    cmd_rows = [r for r in rows if r.section == "*COMMAND"]
    commands: list[CommandDef] = []
    for row in cmd_rows:
        id_str = _cell(row.cells, 1)
        if not id_str or not id_str.isdigit():
            continue
        commands.append(
            CommandDef(
                id=int(id_str),
                alias=_cell(row.cells, 2),
                formula=_cell(row.cells, 3),
            )
        )
    return commands


def _parse_config(rows: list[DDFRow]) -> list[ConfigField]:
    cfg_rows = [r for r in rows if r.section == "*CONFIG"]
    configs: list[ConfigField] = []
    for row in cfg_rows:
        id_str = _cell(row.cells, 1)
        if not id_str or not id_str.isdigit():
            continue
        configs.append(
            ConfigField(
                id=int(id_str),
                alias=_cell(row.cells, 2),
            )
        )
    return configs


def _parse_writes(rows: list[DDFRow]) -> list[WriteCommand]:
    write_rows = [r for r in rows if r.section == "*WRITE"]
    writes: list[WriteCommand] = []
    current_write: WriteCommand | None = None

    for row in write_rows:
        first = _cell(row.cells, 0)
        second = _cell(row.cells, 1)

        # Inline *ARGS row
        is_args = second in ("*ARGS", "ARGS") or first == "*ARGS"
        if is_args:
            if current_write is not None:
                alias = _cell(row.cells, 2)
                c1 = _cell(row.cells, 1)
                arg = ArgsDef(
                    method=c1 if c1 not in ("*ARGS", "ARGS") else None,
                    alias=alias,
                    type=_cell(row.cells, 4) or None,
                    name=_cell(row.cells, 5),
                    value=_cell(row.cells, 6),
                    item=_cell(row.cells, 7) or None,
                    format=_cell(row.cells, 8) or None,
                )
                current_write.args.append(arg)
            continue

        # ARGS data row (continuation)
        if _cell(row.cells, 1) == "ARGS" and current_write is not None:
            alias = _cell(row.cells, 2)
            arg = ArgsDef(
                method=None,
                alias=alias,
                type=_cell(row.cells, 4) or None,
                name=_cell(row.cells, 5),
                value=_cell(row.cells, 6),
                item=_cell(row.cells, 7) or None,
                format=_cell(row.cells, 8) or None,
            )
            current_write.args.append(arg)
            continue

        # Write command header
        alias = _cell(row.cells, 1)
        if not alias:
            continue

        current_write = WriteCommand(
            alias=alias,
            method=_cell(row.cells, 2),
            url=_cell(row.cells, 3) or None,
            datatype=_cell(row.cells, 4) or None,
            formula=_cell(row.cells, 5),
            args=[],
        )
        writes.append(current_write)

    return writes


def _parse_items(rows: list[DDFRow]) -> list[Item]:
    item_rows = [r for r in rows if r.section == "*ITEM"]
    items: list[Item] = []
    for row in item_rows:
        alias = _cell(row.cells, 1)
        if not alias:
            continue
        items.append(
            Item(
                alias=alias.strip(),
                name=_cell(row.cells, 2).strip(),
                id=int(_cell(row.cells, 3)) if _cell(row.cells, 3).isdigit() else 0,
                visibility=_cell(row.cells, 4) or None,
                unit=_cell(row.cells, 5) or None,
                type=_cell(row.cells, 6) or None,
                default=_cell(row.cells, 7) or None,
                wformula=_cell(row.cells, 8) or None,
                rformula=_cell(row.cells, 9) or None,
                polling=_int_or_none(_cell(row.cells, 10, "")),
                comment=_cell(row.cells, 11) or None,
            )
        )
    return items


def _parse_groups(rows: list[DDFRow]) -> list[Group]:
    group_rows = [r for r in rows if r.section == "*GROUP"]
    groups: list[Group] = []
    for row in group_rows:
        # Column order varies: some DDFs use ID;ALIAS;NAME, others ALIAS;ID;NAME
        c1 = _cell(row.cells, 1)
        c2 = _cell(row.cells, 2)
        c3 = _cell(row.cells, 3)

        if not c1:
            continue

        if c1.isdigit():
            groups.append(Group(id=int(c1), alias=c2, name=c3))
        elif c2.isdigit():
            groups.append(Group(id=int(c2), alias=c1, name=c3))
        else:
            continue
    return groups


def _parse_objects(rows: list[DDFRow]) -> list[ObjectDef]:
    obj_rows = [r for r in rows if r.section == "*OBJECT"]
    objects: list[ObjectDef] = []
    for row in obj_rows:
        group_str = _cell(row.cells, 1)
        id_str = _cell(row.cells, 2)
        if not group_str or not group_str.isdigit():
            continue
        if not id_str or not id_str.isdigit():
            continue
        objects.append(
            ObjectDef(
                group=int(group_str),
                id=int(id_str),
                alias=_cell(row.cells, 3),
                type=_int_or_none(_cell(row.cells, 4, "")),
                enum=_int_or_none(_cell(row.cells, 5, "")),
                enumtext=_cell(row.cells, 6) or None,
                enumval=_cell(row.cells, 7) or None,
                min=_float_or_none(_cell(row.cells, 8, "")),
                max=_float_or_none(_cell(row.cells, 9, "")),
                iotype=_int_or_none(_cell(row.cells, 10, "")),
                digits=_int_or_none(_cell(row.cells, 11, "")),
                itemid=_int_or_none(_cell(row.cells, 12, "")),
                unit=_cell(row.cells, 13) or None,
                alarm=_cell(row.cells, 14) or None,
                alarmval=_cell(row.cells, 15) or None,
                alarmtime=_int_or_none(_cell(row.cells, 16, "")),
                outtype=_int_or_none(_cell(row.cells, 17, "")),
                cmditemid=_int_or_none(_cell(row.cells, 18, "")),
                command=_cell(row.cells, 19) or None,
                commandenum=_cell(row.cells, 20) or None,
                commandval=_cell(row.cells, 21) or None,
                viewtype=_int_or_none(_cell(row.cells, 22, "")),
                log=_int_or_none(_cell(row.cells, 23, "")),
            )
        )
    return objects


def parse_ddf(path: Path) -> DDF:
    """Parse a DDF CSV file into a typed AST."""
    rows = lex_ddf(path)
    if not rows:
        raise DDFSyntaxError("Empty DDF file", line=1)

    signature = _parse_signature(rows)
    metadata, params = _parse_general(rows)
    commands = _parse_commands(rows)
    config = _parse_config(rows)
    writes = _parse_writes(rows)
    items = _parse_items(rows)
    groups = _parse_groups(rows)
    objects = _parse_objects(rows)

    raw_source = path.read_bytes().decode("utf-8", errors="replace")

    return DDF(
        signature=signature,
        general_metadata=metadata,
        general_params=params,
        commands=commands,
        config=config,
        reads=[],  # *READ is empty in known DDFs
        writes=writes,
        items=items,
        groups=groups,
        objects=objects,
        raw_source=raw_source,
    )
