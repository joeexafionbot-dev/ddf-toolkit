"""Tests for the DDF linter — one test per rule with passing and failing cases."""

from __future__ import annotations

from pathlib import Path

from ddf_toolkit.linter import lint_ddf
from ddf_toolkit.linter.rules import (
    DDF001,
    DDF002,
    DDF003,
    DDF004,
    DDF005,
    DDF006,
    DDF007,
    DDF008,
    DDF009,
    DDF010,
)
from ddf_toolkit.parser import parse_ddf
from ddf_toolkit.parser.ast import (
    DDF,
    ArgsDef,
    CommandDef,
    GeneralMetadata,
    GeneralParams,
    Item,
    WriteCommand,
)

FIXTURES = Path(__file__).parent.parent / "fixtures" / "ddfs"


def _make_ddf(**kwargs: object) -> DDF:
    """Build a minimal DDF for testing, with overridable fields."""
    defaults = {
        "signature": None,
        "general_metadata": GeneralMetadata(
            device="Test",
            manufacturer="Test",
            type="Test",
            protocol="REST-API (DDF)",
            model_nr="1",
            version_nr="1",
            id="0x0000000000000000",
            min_control_version="V1000-01",
            timestamp="2026-01-01 00:00:00",
        ),
        "general_params": GeneralParams(
            connection="DOMAIN",
            authentification="NONE",
            domain="http://test",
            debugport=8500,
        ),
        "commands": [],
        "config": [],
        "reads": [],
        "writes": [],
        "items": [],
        "groups": [],
        "objects": [],
        "raw_source": "",
    }
    defaults.update(kwargs)
    return DDF(**defaults)  # type: ignore[arg-type]


# ---- Pilot DDF integration tests ----


def test_microsoft_calendar_lint_clean():
    path = FIXTURES / "Microsoft.Gateway.REST-API (DDF).Calender.1(0x0D00007700010100).csv"
    ddf = parse_ddf(path)
    findings = lint_ddf(ddf)
    errors = [f for f in findings if f.severity == "error"]
    assert len(errors) == 0, f"Unexpected errors: {errors}"


def test_daikin_stylish_lint_clean():
    path = FIXTURES / "Daikin.Air conditioner.REST-API (DDF).Stylish.1(0x0D00000D00010100).csv"
    ddf = parse_ddf(path)
    findings = lint_ddf(ddf)
    errors = [f for f in findings if f.severity == "error"]
    assert len(errors) == 0, f"Unexpected errors: {errors}"


# ---- DDF001: *WRITE references undefined ARG ----


def test_ddf001_pass():
    ddf = _make_ddf(
        writes=[
            WriteCommand(
                alias="GETDATA",
                method="GET",
                url=None,
                datatype="JSON",
                formula="",
                args=[ArgsDef(method=None, alias="GETDATA", type="url", name="/v1/data", value="")],
            ),
        ]
    )
    assert DDF001().check(ddf) == []


def test_ddf001_fail():
    ddf = _make_ddf(
        writes=[
            WriteCommand(
                alias="GETDATA",
                method="GET",
                url=None,
                datatype="JSON",
                formula="",
                args=[ArgsDef(method=None, alias="NONEXISTENT", type="url", name="/v1", value="")],
            ),
        ]
    )
    findings = DDF001().check(ddf)
    assert len(findings) == 1
    assert findings[0].code == "DDF001"


# ---- DDF002: *FORMULA references undefined DATA path ----


def test_ddf002_pass():
    ddf = _make_ddf(
        writes=[
            WriteCommand(
                alias="GETDATA",
                method="GET",
                url=None,
                datatype="JSON",
                formula="X.1 := GETDATA.VALUE.temp;",
            ),
        ],
    )
    assert DDF002().check(ddf) == []


def test_ddf002_fail():
    ddf = _make_ddf(
        writes=[
            WriteCommand(
                alias="GETDATA",
                method="GET",
                url=None,
                datatype="JSON",
                formula="X.1 := UNKNOWN.VALUE.temp;",
            ),
        ],
    )
    findings = DDF002().check(ddf)
    assert len(findings) >= 1
    assert findings[0].code == "DDF002"


# ---- DDF003: *ITEM declared but never referenced ----


def test_ddf003_pass():
    ddf = _make_ddf(
        items=[Item(alias="TEMP", name="Temperature", id=10, rformula="X.10 := 1;")],
    )
    assert DDF003().check(ddf) == []


def test_ddf003_fail():
    ddf = _make_ddf(
        items=[Item(alias="ORPHAN", name="Orphan", id=99)],
    )
    findings = DDF003().check(ddf)
    assert len(findings) == 1
    assert findings[0].code == "DDF003"
    assert "ORPHAN" in findings[0].message


# ---- DDF004: *LISTENER port outside 8500-8600 ----


def test_ddf004_pass():
    ddf = _make_ddf(
        general_params=GeneralParams(
            connection="DOMAIN",
            authentification="NONE",
            domain="http://test",
            extra={"LISTENER_PORT": "8550"},
        ),
    )
    assert DDF004().check(ddf) == []


def test_ddf004_fail():
    ddf = _make_ddf(
        general_params=GeneralParams(
            connection="DOMAIN",
            authentification="NONE",
            domain="http://test",
            extra={"LISTENER_PORT": "9999"},
        ),
    )
    findings = DDF004().check(ddf)
    assert len(findings) == 1
    assert findings[0].code == "DDF004"


def test_ddf004_no_listener():
    """No LISTENER_PORT => no finding."""
    ddf = _make_ddf()
    assert DDF004().check(ddf) == []


# ---- DDF005: DEBUGPORT outside 8500-8600 ----


def test_ddf005_pass():
    ddf = _make_ddf(
        general_params=GeneralParams(
            connection="DOMAIN", authentification="NONE", domain="", debugport=8500
        ),
    )
    assert DDF005().check(ddf) == []


def test_ddf005_fail():
    ddf = _make_ddf(
        general_params=GeneralParams(
            connection="DOMAIN", authentification="NONE", domain="", debugport=9999
        ),
    )
    findings = DDF005().check(ddf)
    assert len(findings) == 1
    assert findings[0].code == "DDF005"


# ---- DDF006: MIN_CONTROL_VERSION not parseable ----


def test_ddf006_pass():
    ddf = _make_ddf()  # default has V1000-01
    assert DDF006().check(ddf) == []


def test_ddf006_fail():
    ddf = _make_ddf(
        general_metadata=GeneralMetadata(
            device="T",
            manufacturer="T",
            type="T",
            protocol="REST-API (DDF)",
            model_nr="1",
            version_nr="1",
            id="0x0",
            min_control_version="garbage",
            timestamp="2026-01-01",
        ),
    )
    findings = DDF006().check(ddf)
    assert len(findings) == 1
    assert findings[0].code == "DDF006"


def test_ddf006_empty_version():
    """Empty MIN_CONTROL_VERSION => no finding."""
    ddf = _make_ddf(
        general_metadata=GeneralMetadata(
            device="T",
            manufacturer="T",
            type="T",
            protocol="REST-API (DDF)",
            model_nr="1",
            version_nr="1",
            id="0x0",
            min_control_version="",
            timestamp="2026-01-01",
        ),
    )
    assert DDF006().check(ddf) == []


# ---- DDF007: Duplicate *ITEM alias ----


def test_ddf007_pass():
    ddf = _make_ddf(
        items=[
            Item(alias="A", name="A", id=1),
            Item(alias="B", name="B", id=2),
        ],
    )
    assert DDF007().check(ddf) == []


def test_ddf007_fail():
    ddf = _make_ddf(
        items=[
            Item(alias="TEMP", name="Temp1", id=1),
            Item(alias="TEMP", name="Temp2", id=2),
        ],
    )
    findings = DDF007().check(ddf)
    assert len(findings) == 1
    assert findings[0].code == "DDF007"
    assert findings[0].severity == "error"


# ---- DDF008: Duplicate *ARGS name ----


def test_ddf008_pass():
    ddf = _make_ddf(
        writes=[
            WriteCommand(
                alias="W",
                method="GET",
                url=None,
                datatype="JSON",
                formula="",
                args=[
                    ArgsDef(method=None, alias="W", type="url", name="/path", value=""),
                    ArgsDef(method=None, alias="W", type="arg", name="param", value=""),
                ],
            ),
        ]
    )
    assert DDF008().check(ddf) == []


def test_ddf008_fail():
    ddf = _make_ddf(
        writes=[
            WriteCommand(
                alias="W",
                method="GET",
                url=None,
                datatype="JSON",
                formula="",
                args=[
                    ArgsDef(method=None, alias="W", type="url", name="/path", value=""),
                    ArgsDef(method=None, alias="W", type="url", name="/path", value="x"),
                ],
            ),
        ]
    )
    findings = DDF008().check(ddf)
    assert len(findings) == 1
    assert findings[0].code == "DDF008"


# ---- DDF009: AUTHENTIFICATION = PASSWORD without CONFIG ----


def test_ddf009_pass_no_auth():
    ddf = _make_ddf()  # default is NONE
    assert DDF009().check(ddf) == []


def test_ddf009_pass_with_config():
    ddf = _make_ddf(
        general_params=GeneralParams(
            connection="DOMAIN",
            authentification="PASSWORD",
            domain="",
            extra={"PASSWORD": "secret"},
        ),
    )
    assert DDF009().check(ddf) == []


def test_ddf009_fail():
    ddf = _make_ddf(
        general_params=GeneralParams(
            connection="DOMAIN",
            authentification="PASSWORD",
            domain="",
        ),
    )
    findings = DDF009().check(ddf)
    assert len(findings) == 1
    assert findings[0].code == "DDF009"


# ---- DDF010: *ITEM formula references unknown source ----


def test_ddf010_pass():
    ddf = _make_ddf(
        writes=[WriteCommand(alias="GETDATA", method="GET", url=None, datatype="JSON", formula="")],
        items=[Item(alias="T", name="T", id=1, rformula="GETDATA.F := 1;")],
    )
    assert DDF010().check(ddf) == []


def test_ddf010_fail():
    ddf = _make_ddf(
        items=[Item(alias="T", name="T", id=1, rformula="NONEXISTENT.F := 1;")],
    )
    findings = DDF010().check(ddf)
    assert len(findings) == 1
    assert findings[0].code == "DDF010"
    assert "NONEXISTENT" in findings[0].message


def test_ddf010_command_alias_ok():
    """Triggering a COMMAND alias should be valid."""
    ddf = _make_ddf(
        commands=[CommandDef(id=0, alias="REFRESH", formula="REFRESH.F := 1;")],
        items=[Item(alias="T", name="T", id=1, wformula="REFRESH.F := 1;")],
    )
    assert DDF010().check(ddf) == []
