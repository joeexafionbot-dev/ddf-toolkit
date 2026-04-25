"""Tests for the formula parser."""

from __future__ import annotations

import pytest

from ddf_toolkit.formula import parse_formula
from ddf_toolkit.formula.evaluator import UnsupportedFormulaError, evaluate


def test_parse_simple():
    ast = parse_formula("X.50 := 1;")
    assert ast.valid
    assert ast.tokens > 0


def test_parse_complex_if():
    ast = parse_formula("IF X.50 THEN X.60 := 0; ELSE X.60 := 1; ENDIF;")
    assert ast.valid


def test_parse_oversized_formula():
    ast = parse_formula("X" * 5000)
    assert not ast.valid
    assert "exceeds" in (ast.error or "")


def test_evaluate_raises_not_implemented():
    with pytest.raises(NotImplementedError, match="Sprint 1"):
        evaluate("X := 1;")


def test_unsupported_formula_error():
    err = UnsupportedFormulaError("ARRAY.MAX")
    assert "ARRAY.MAX" in str(err)
    assert "formula-coverage.md" in str(err)
