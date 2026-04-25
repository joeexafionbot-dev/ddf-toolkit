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


def test_block_comments():
    tokens = tokenize("X := 1; /* this is a comment */ Y := 2;")
    identifiers = [t.value for t in tokens if t.type == TokenType.IDENTIFIER]
    assert "X" in identifiers
    assert "Y" in identifiers
    # Comment content should not appear as tokens
    assert "this" not in identifiers
    assert "comment" not in identifiers


def test_switch_case():
    tokens = tokenize("SWITCH X.0 CASE 12: DEBUG(CASE12); DEFAULT: DEBUG(DEF); ENDSWITCH;")
    types = [t.type for t in tokens if t.type != TokenType.EOF]
    assert TokenType.SWITCH in types
    assert TokenType.CASE in types
    assert TokenType.DEFAULT in types
    assert TokenType.ENDSWITCH in types
    assert TokenType.COLON in types


def test_for_loop():
    tokens = tokenize("FOR x := 1 TO 10 BY 1 DO X.1 := x; ENDFOR;")
    types = [t.type for t in tokens if t.type != TokenType.EOF]
    assert TokenType.FOR in types
    assert TokenType.TO in types
    assert TokenType.BY in types
    assert TokenType.DO in types
    assert TokenType.ENDFOR in types


def test_bitwise_operators():
    tokens = tokenize("a >> 2 & b | c &~ d")
    types = [t.type for t in tokens if t.type != TokenType.EOF]
    assert TokenType.SHR in types
    assert TokenType.BAND in types
    assert TokenType.BOR in types
    assert TokenType.BANDNOT in types


def test_power_operator():
    tokens = tokenize("x ^ 2")
    types = [t.type for t in tokens if t.type != TokenType.EOF]
    assert TokenType.CARET in types


def test_andnot_operator():
    tokens = tokenize("a &! b")
    types = [t.type for t in tokens if t.type != TokenType.EOF]
    assert TokenType.ANDNOT in types


def test_real_formula_from_pilot_ddf():
    """Tokenize a real formula from the Microsoft Calendar DDF."""
    formula = (
        "IF (GETTOKEN.HTTP_CODE==200) && ISEQUAL(GETTOKEN.VALUE.token_type,'Bearer') THEN "
        "X.192 := 'Token received'; "
        "X.201 := 1; "
        "ENDIF;"
    )
    tokens = tokenize(formula)
    types = [t.type for t in tokens if t.type != TokenType.EOF]
    assert TokenType.IF in types
    assert TokenType.THEN in types
    assert TokenType.ENDIF in types
    assert TokenType.EQ in types
    assert TokenType.AND in types
    assert TokenType.STRING in types
