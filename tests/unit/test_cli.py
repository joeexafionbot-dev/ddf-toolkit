"""Tests for the CLI entry point."""

from __future__ import annotations

from typer.testing import CliRunner

from ddf_toolkit.cli import app

runner = CliRunner()


def test_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "DDF Toolkit" in result.output


def test_version():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "ddf-toolkit" in result.output


def test_validate_pilot_ddfs():
    result = runner.invoke(
        app,
        [
            "validate",
            "tests/fixtures/ddfs/Microsoft.Gateway.REST-API (DDF).Calender.1(0x0D00007700010100).csv",
            "tests/fixtures/ddfs/Daikin.Air conditioner.REST-API (DDF).Stylish.1(0x0D00000D00010100).csv",
        ],
    )
    assert result.exit_code == 0
    assert "PASS" in result.output
