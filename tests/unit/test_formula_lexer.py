"""Tests for the formula lexer."""

from __future__ import annotations

import pytest

from ddf_toolkit.formula.lexer import TokenType, tokenize


def test_simple_assignment():
    tokens = tokenize("X.50 := 1;")
    types = [t.type for t in tokens if t.type != TokenType.EOF]
    assert TokenType.IDENTIFIER in types
    assert TokenType.ASSIGN in types
    assert TokenType.NUMBER in types
    assert TokenType.SEMICOLON in types


def test_if_then_else():
    tokens = tokenize("IF X.50 THEN X.60 := 0; ENDIF;")
    types = [t.type for t in tokens if t.type != TokenType.EOF]
    assert TokenType.IF in types
    assert TokenType.THEN in types
    assert TokenType.ENDIF in types


def test_comparison_operators():
    tokens = tokenize("a == b && c != d || e <= f")
    types = [t.type for t in tokens if t.type != TokenType.EOF]
    assert TokenType.EQ in types
    assert TokenType.AND in types
    assert TokenType.NEQ in types
    assert TokenType.OR in types
    assert TokenType.LTE in types


def test_string_literal():
    tokens = tokenize("X := 'hello world';")
    string_tokens = [t for t in tokens if t.type == TokenType.STRING]
    assert len(string_tokens) == 1
    assert string_tokens[0].value == "hello world"


def test_formula_size_limit():
    with pytest.raises(ValueError, match="exceeds"):
        tokenize("X" * 5000)


def test_arithmetic():
    tokens = tokenize("(a + b) * c / d - e")
    types = [t.type for t in tokens if t.type != TokenType.EOF]
    assert TokenType.LPAREN in types
    assert TokenType.PLUS in types
    assert TokenType.STAR in types
    assert TokenType.SLASH in types
    assert TokenType.MINUS in types
