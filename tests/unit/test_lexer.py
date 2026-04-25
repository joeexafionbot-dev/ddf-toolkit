"""Tests for the DDF CSV lexer."""

from __future__ import annotations

from pathlib import Path

from ddf_toolkit.parser.lexer import lex_ddf

FIXTURES = Path(__file__).parent.parent / "fixtures" / "ddfs"


def test_lex_microsoft_calendar():
    path = FIXTURES / "Microsoft.Gateway.REST-API (DDF).Calender.1(0x0D00007700010100).csv"
    rows = lex_ddf(path)
    assert len(rows) > 0
    sections = {r.section for r in rows}
    assert "*SIGNATURE" in sections
    assert "*GENERAL" in sections
    assert "*WRITE" in sections
    assert "*ITEM" in sections


def test_lex_daikin_stylish():
    path = FIXTURES / "Daikin.Air conditioner.REST-API (DDF).Stylish.1(0x0D00000D00010100).csv"
    rows = lex_ddf(path)
    assert len(rows) > 0
    sections = {r.section for r in rows}
    assert "*GENERAL" in sections
    assert "*WRITE" in sections


def test_comment_lines_skipped():
    path = FIXTURES / "Microsoft.Gateway.REST-API (DDF).Calender.1(0x0D00007700010100).csv"
    rows = lex_ddf(path)
    # No row should start with #
    for row in rows:
        assert not row.cells[0].strip().startswith("#")
