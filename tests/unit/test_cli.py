"""Tests for the CLI entry point."""

from __future__ import annotations

from typer.testing import CliRunner

from ddf_toolkit.cli import app

runner = CliRunner()

MS_CAL = "tests/fixtures/ddfs/microsoft_calendar.csv"


def test_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "DDF Toolkit" in result.output


def test_version():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "ddf-toolkit" in result.output
    assert "0.2.0" in result.output


def test_validate_pass():
    result = runner.invoke(app, ["validate", MS_CAL])
    assert result.exit_code == 0
    assert "PASS" in result.output


def test_validate_nonexistent_file():
    result = runner.invoke(app, ["validate", "nonexistent.csv"])
    assert result.exit_code == 1
    assert "FAIL" in result.output


def test_validate_json_format():
    result = runner.invoke(app, ["validate", "--format", "json", MS_CAL])
    assert result.exit_code == 0
    assert '"status": "PASS"' in result.output


def test_validate_quiet():
    result = runner.invoke(app, ["--quiet", "validate", MS_CAL])
    assert result.exit_code == 0
    assert "PASS" not in result.output


def test_lint_pass():
    result = runner.invoke(app, ["lint", MS_CAL])
    assert result.exit_code == 0
    assert "PASS" in result.output


def test_lint_json_format():
    result = runner.invoke(app, ["lint", "--format", "json", MS_CAL])
    assert result.exit_code == 0
    assert "[" in result.output


def test_parse_json():
    result = runner.invoke(app, ["parse", "--json", MS_CAL])
    assert result.exit_code == 0
    assert '"device": "Calender"' in result.output


def test_formula_parse():
    result = runner.invoke(app, ["formula", "X.50 := 1;"])
    assert result.exit_code == 0
    assert "FormulaAST" in result.output


def test_simulate_exit_code_3():
    result = runner.invoke(app, ["simulate", "dummy.csv", "--capture", "dummy.har"])
    assert result.exit_code == 3


def test_sign_missing_key_exit_code_2():
    result = runner.invoke(app, ["sign", "dummy.csv"])
    assert result.exit_code == 2


def test_keygen():
    result = runner.invoke(app, ["keygen", "--test", "-o", "/tmp/ddf-test-key.pem"])
    assert result.exit_code == 0
    assert "Private key" in result.output
    assert "Public key" in result.output
