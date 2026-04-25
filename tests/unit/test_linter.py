"""Tests for the DDF linter."""

from __future__ import annotations

from pathlib import Path

from ddf_toolkit.linter import lint_ddf
from ddf_toolkit.parser import parse_ddf

FIXTURES = Path(__file__).parent.parent / "fixtures" / "ddfs"


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


def test_debugport_in_range():
    """Both pilots have DEBUGPORT=8500, which is in range."""
    path = FIXTURES / "Microsoft.Gateway.REST-API (DDF).Calender.1(0x0D00007700010100).csv"
    ddf = parse_ddf(path)
    findings = lint_ddf(ddf)
    ddf005 = [f for f in findings if f.code == "DDF005"]
    assert len(ddf005) == 0
