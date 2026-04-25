"""AST → CSV serializer for DDF files.

Produces canonical CSV bytes from a DDF AST that round-trip through
the parser: parse(serialize(ast)) ≅ ast (ignoring raw_source).
"""

from __future__ import annotations

from ddf_toolkit.parser.ast import DDF

# Standard column count for padding (matches pilot DDFs)
_PAD_COLS = 23


def serialize_ddf(ddf: DDF) -> str:
    """Serialize a DDF AST to CSV string."""
    lines: list[str] = []

    # *SIGNATURE
    if ddf.signature:
        lines.append("*SIGNATURE")
        lines.append(_kv("SIGN_ALGO", ddf.signature.sign_algo))
        lines.append(_kv("SIGN_DATE", ddf.signature.sign_date))
        lines.append(_kv("FILE_VERDATE", ddf.signature.file_verdate))
        lines.append(_kv("SIGNATURE", ddf.signature.signature))

    # *GENERAL Block 1 — device metadata
    lines.append(_section_header("*GENERAL"))
    lines.append(_kv("DEVICE", ddf.general_metadata.device))
    lines.append(_kv("MANUFACTURER", ddf.general_metadata.manufacturer))
    lines.append(_kv("TYPE", ddf.general_metadata.type))
    lines.append(_kv("PROTOCOL", ddf.general_metadata.protocol))
    lines.append(_kv("MODEL_NR", ddf.general_metadata.model_nr))
    lines.append(_kv("VERSION_NR", ddf.general_metadata.version_nr))
    lines.append(_kv("ID", ddf.general_metadata.id))
    lines.append(_kv("MIN_CONTROL_VERSION", ddf.general_metadata.min_control_version))
    lines.append(_kv("TIMESTAMP", ddf.general_metadata.timestamp))

    # *GENERAL Block 2 — connection/auth params
    lines.append(_section_header("*GENERAL"))
    lines.append(_kv_padded("CONNECTION", ddf.general_params.connection))
    lines.append(_kv_padded("AUTHENTIFICATION", ddf.general_params.authentification))

    domain_line = f";DOMAIN;{ddf.general_params.domain}"
    if ddf.general_params.domain_alt:
        domain_line += f";;{ddf.general_params.domain_alt}"
    lines.append(_pad(domain_line))

    if ddf.general_params.slavesmax is not None:
        lines.append(_kv_padded("SLAVESMAX", str(ddf.general_params.slavesmax)))

    # Extra GPARAM fields
    for key, val in ddf.general_params.extra.items():
        lines.append(_kv_padded(key, val))

    if ddf.general_params.debugport is not None:
        lines.append(_kv_padded("DEBUGPORT", str(ddf.general_params.debugport)))

    if ddf.general_metadata.version_info is not None:
        lines.append(f";VERSION_INFO;{ddf.general_metadata.version_info}")
    if ddf.general_metadata.version_user is not None:
        lines.append(f";VERSION_USER;{ddf.general_metadata.version_user}")
    if ddf.general_metadata.revision is not None:
        lines.append(f";REVISION;{ddf.general_metadata.revision};;")

    # *COMMAND
    if ddf.commands:
        lines.append(_section_with_cols("*COMMAND", ["ID", "ALIAS", "FORMULA"]))
        for cmd in ddf.commands:
            formula = _quote_formula(cmd.formula)
            lines.append(_pad(f";{cmd.id};{cmd.alias};{formula}"))

    # *CONFIG
    if ddf.config:
        lines.append(_section_with_cols("*CONFIG", ["ID", "ALIAS"]))
        for cfg in ddf.config:
            lines.append(_pad(f";{cfg.id};{cfg.alias}"))

    # *READ
    lines.append(_section_with_cols("*READ", ["ALIAS", "METHOD", "URL", "DATATYPE", "POLLING"]))
    for read in ddf.reads:
        lines.append(
            _pad(f";{read.alias};{read.method};{read.url};{read.datatype};{read.polling or ''}")
        )
    if not ddf.reads:
        lines.append(_section_header(""))  # empty row

    # *WRITE
    lines.append(_section_with_cols("*WRITE", ["ALIAS", "METHOD", "URL", "DATATYPE", "FORMULA"]))
    # Filter header pseudo-writes
    real_writes = [w for w in ddf.writes if w.alias.upper() != "ALIAS"]
    for write in real_writes:
        formula = _quote_formula(write.formula)
        lines.append(
            _pad(
                f";{write.alias};{write.method};{write.url or ''};{write.datatype or ''};{formula}"
            )
        )
        # Inline *ARGS
        if write.args:
            lines.append(";*ARGS;METHOD;ALIAS;TYPE;NAME;VALUE;ITEM;FORMAT" + ";" * (_PAD_COLS - 8))
            for arg in write.args:
                lines.append(
                    _pad(
                        f";ARGS;{arg.alias};;{arg.type or ''};{arg.name};"
                        f"{arg.value};{arg.item or ''};{arg.format or ''}"
                    )
                )

    # *GROUP
    if ddf.groups:
        lines.append(_section_with_cols("*GROUP", ["ID", "ALIAS", "NAME"]))
        for grp in ddf.groups:
            lines.append(_pad(f";{grp.id};{grp.alias};{grp.name}"))

    # *ITEM
    if ddf.items:
        lines.append(
            _section_with_cols(
                "*ITEM",
                [
                    "ALIAS",
                    "NAME",
                    "ID",
                    "VISIBILITY",
                    "UNIT",
                    "TYPE",
                    "DEFAULT",
                    "WFORMULA",
                    "RFORMULA",
                    "POLLING",
                ],
            )
        )
        # Filter out header pseudo-items (parser artifact)
        real_items = [i for i in ddf.items if i.alias.upper() != "ALIAS"]
        for item in real_items:
            wf = _quote_formula(item.wformula or "")
            rf = _quote_formula(item.rformula or "")
            lines.append(
                _pad(
                    f";{item.alias};{item.name};{item.id};"
                    f"{item.visibility or ''};{item.unit or ''};"
                    f"{item.type or ''};{item.default or ''};"
                    f"{wf};{rf};{item.polling or ''}"
                )
            )

    # *OBJECT
    if ddf.objects:
        lines.append(
            _section_with_cols(
                "*OBJECT",
                [
                    "GROUP",
                    "ID",
                    "ALIAS",
                    "TYPE",
                    "ENUM",
                    "ENUMTEXT",
                    "ENUMVAL",
                    "MIN",
                    "MAX",
                    "IOTYPE",
                    "DIGITS",
                    "ITEMID",
                    "UNIT",
                    "ALARM",
                    "ALARMVAL",
                    "ALARMTIME",
                    "OUTTYPE",
                    "CMDITEMID",
                    "COMMAND",
                    "COMMANDENUM",
                    "COMMANDVAL",
                    "VIEWTYPE",
                    "LOG",
                ],
            )
        )
        for obj in ddf.objects:
            parts = [
                str(obj.group),
                str(obj.id),
                obj.alias,
                _opt_int(obj.type),
                _opt_int(obj.enum),
                obj.enumtext or "",
                obj.enumval or "",
                _opt_float(obj.min),
                _opt_float(obj.max),
                _opt_int(obj.iotype),
                _opt_int(obj.digits),
                _opt_int(obj.itemid),
                obj.unit or "",
                obj.alarm or "",
                obj.alarmval or "",
                _opt_int(obj.alarmtime),
                _opt_int(obj.outtype),
                _opt_int(obj.cmditemid),
                obj.command or "",
                obj.commandenum or "",
                obj.commandval or "",
                _opt_int(obj.viewtype),
                _opt_int(obj.log),
            ]
            lines.append(";" + ";".join(parts))

    lines.append("")  # trailing newline
    return "\n".join(lines) + "\n"


# -- Helpers -----------------------------------------------------------------


def _section_header(name: str) -> str:
    """Section header row with padding."""
    return name + ";" * _PAD_COLS


def _section_with_cols(name: str, cols: list[str]) -> str:
    """Section header with column names."""
    header = name + ";" + ";".join(cols)
    remaining = _PAD_COLS - len(cols)
    if remaining > 0:
        header += ";" * remaining
    return header


def _kv(key: str, val: str) -> str:
    """Simple key-value row: ;KEY;VALUE;;"""
    return f";{key};{val};;"


def _kv_padded(key: str, val: str) -> str:
    """Key-value row with full padding."""
    return _pad(f";{key};{val}")


def _pad(line: str) -> str:
    """Pad a line to _PAD_COLS total semicolons."""
    current = line.count(";")
    if current < _PAD_COLS:
        line += ";" * (_PAD_COLS - current)
    return line


def _quote_formula(formula: str) -> str:
    """Wrap a formula in triple-quotes if it contains semicolons or newlines.

    DDF CSV format: formulas with ; or newlines are wrapped in triple double-quotes.
    Internal double-quotes are escaped as double-double-quotes ("").
    """
    if not formula:
        return ""
    needs_quoting = ";" in formula or "\n" in formula or '"' in formula
    if needs_quoting:
        # Escape internal " as "" (CSV convention within DDF triple-quote)
        escaped = formula.replace('"', '""')
        return f'"""{escaped}"""'
    return formula


def _opt_int(val: int | None) -> str:
    return str(val) if val is not None else ""


def _opt_float(val: float | None) -> str:
    if val is None:
        return ""
    if val == int(val):
        return str(int(val))
    return str(val)
