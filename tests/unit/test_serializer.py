"""Tests for the AST → CSV serializer.

Key test: parse(serialize(parse(pilot.csv))) ≅ parse(pilot.csv)
(structural equality, ignoring raw_source).
"""

from __future__ import annotations

from pathlib import Path

from ddf_toolkit.parser.ast import DDF
from ddf_toolkit.parser.parser import parse_ddf
from ddf_toolkit.serializer import serialize_ddf

DDFS = Path(__file__).parent.parent / "fixtures" / "ddfs"


def _ast_equal(a: DDF, b: DDF) -> list[str]:
    """Compare two DDFs structurally, ignoring raw_source. Returns list of diffs."""
    diffs: list[str] = []

    # Signature
    if (a.signature is None) != (b.signature is None):
        diffs.append(f"signature: {a.signature!r} vs {b.signature!r}")
    elif a.signature and b.signature and a.signature.sign_algo != b.signature.sign_algo:
        diffs.append(f"signature.sign_algo: {a.signature.sign_algo!r} vs {b.signature.sign_algo!r}")

    # General metadata
    for field in [
        "device",
        "manufacturer",
        "type",
        "protocol",
        "model_nr",
        "version_nr",
        "id",
        "min_control_version",
    ]:
        va = getattr(a.general_metadata, field)
        vb = getattr(b.general_metadata, field)
        if va != vb:
            diffs.append(f"general_metadata.{field}: {va!r} vs {vb!r}")

    # General params
    for field in ["connection", "authentification", "domain", "debugport"]:
        va = getattr(a.general_params, field)
        vb = getattr(b.general_params, field)
        if va != vb:
            diffs.append(f"general_params.{field}: {va!r} vs {vb!r}")

    # Commands
    if len(a.commands) != len(b.commands):
        diffs.append(f"commands count: {len(a.commands)} vs {len(b.commands)}")
    else:
        for i, (ca, cb) in enumerate(zip(a.commands, b.commands, strict=False)):
            if ca.alias != cb.alias:
                diffs.append(f"commands[{i}].alias: {ca.alias!r} vs {cb.alias!r}")

    # Config
    if len(a.config) != len(b.config):
        diffs.append(f"config count: {len(a.config)} vs {len(b.config)}")

    # Items (filter header pseudo-items)
    a_items = [i for i in a.items if i.alias.upper() != "ALIAS"]
    b_items = [i for i in b.items if i.alias.upper() != "ALIAS"]
    if len(a_items) != len(b_items):
        diffs.append(f"items count: {len(a_items)} vs {len(b_items)}")
    else:
        for i, (ia, ib) in enumerate(zip(a_items, b_items, strict=False)):
            if ia.alias != ib.alias:
                diffs.append(f"items[{i}].alias: {ia.alias!r} vs {ib.alias!r}")
            if ia.id != ib.id:
                diffs.append(f"items[{i}].id: {ia.id} vs {ib.id}")

    # Writes (filter header pseudo-writes)
    a_writes = [w for w in a.writes if w.alias.upper() != "ALIAS"]
    b_writes = [w for w in b.writes if w.alias.upper() != "ALIAS"]
    if len(a_writes) != len(b_writes):
        diffs.append(f"writes count: {len(a_writes)} vs {len(b_writes)}")
    else:
        for i, (wa, wb) in enumerate(zip(a_writes, b_writes, strict=False)):
            if wa.alias != wb.alias:
                diffs.append(f"writes[{i}].alias: {wa.alias!r} vs {wb.alias!r}")

    # Groups
    if len(a.groups) != len(b.groups):
        diffs.append(f"groups count: {len(a.groups)} vs {len(b.groups)}")

    # Objects
    if len(a.objects) != len(b.objects):
        diffs.append(f"objects count: {len(a.objects)} vs {len(b.objects)}")

    return diffs


class TestRoundTrip:
    """Core test: parse → serialize → parse produces equivalent AST."""

    def test_microsoft_calendar_round_trip(self):
        original = parse_ddf(DDFS / "microsoft_calendar.csv")
        csv_text = serialize_ddf(original)
        # Write to temp file and re-parse
        tmp = Path("/tmp/ddf_rt_ms_cal.csv")
        tmp.write_text(csv_text, encoding="utf-8")
        reparsed = parse_ddf(tmp)

        diffs = _ast_equal(original, reparsed)
        assert not diffs, "Round-trip diffs:\n" + "\n".join(diffs)

    def test_daikin_stylish_round_trip(self):
        original = parse_ddf(DDFS / "daikin_stylish.csv")
        csv_text = serialize_ddf(original)
        tmp = Path("/tmp/ddf_rt_daikin.csv")
        tmp.write_text(csv_text, encoding="utf-8")
        reparsed = parse_ddf(tmp)

        diffs = _ast_equal(original, reparsed)
        assert not diffs, "Round-trip diffs:\n" + "\n".join(diffs)


class TestSerializeBasics:
    def test_produces_string(self):
        ddf = parse_ddf(DDFS / "microsoft_calendar.csv")
        csv = serialize_ddf(ddf)
        assert isinstance(csv, str)
        assert len(csv) > 100

    def test_contains_sections(self):
        ddf = parse_ddf(DDFS / "microsoft_calendar.csv")
        csv = serialize_ddf(ddf)
        assert "*SIGNATURE" in csv
        assert "*GENERAL" in csv
        assert "*COMMAND" in csv
        assert "*CONFIG" in csv
        assert "*WRITE" in csv
        assert "*ITEM" in csv
        assert "*OBJECT" in csv

    def test_contains_metadata(self):
        ddf = parse_ddf(DDFS / "microsoft_calendar.csv")
        csv = serialize_ddf(ddf)
        assert "Microsoft" in csv
        assert "Calender" in csv
        assert "0x0D00007700010100" in csv

    def test_formulas_quoted(self):
        ddf = parse_ddf(DDFS / "microsoft_calendar.csv")
        csv = serialize_ddf(ddf)
        # Formulas with semicolons should be triple-quoted
        assert '"""' in csv

    def test_semicolon_delimiter(self):
        ddf = parse_ddf(DDFS / "microsoft_calendar.csv")
        csv = serialize_ddf(ddf)
        # Most lines should use semicolons (except bare section names like *SIGNATURE)
        lines_with_semis = sum(1 for line in csv.strip().split("\n") if ";" in line)
        total_lines = sum(1 for line in csv.strip().split("\n") if line.strip())
        assert lines_with_semis / total_lines > 0.85  # Multi-line formulas have continuation lines
