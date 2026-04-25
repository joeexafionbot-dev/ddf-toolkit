"""Tests for the formula recursive-descent parser."""

from __future__ import annotations

import pytest

from ddf_toolkit.formula import parse_formula
from ddf_toolkit.formula.ast import (
    AssignStmt,
    BinaryOp,
    ExprStmt,
    FunctionCall,
    IfStmt,
    NumberLiteral,
    PathAccess,
    StringLiteral,
    UnaryOp,
)
from ddf_toolkit.formula.evaluator import UnsupportedFormulaError, evaluate

# -- Basic parsing -----------------------------------------------------------


def test_parse_simple_assignment():
    ast = parse_formula("X.50 := 1;")
    assert ast.valid
    assert ast.script is not None
    assert len(ast.script.statements) == 1
    stmt = ast.script.statements[0]
    assert isinstance(stmt, AssignStmt)
    assert isinstance(stmt.target, PathAccess)
    assert stmt.target.parts == ["X", "50"]
    assert isinstance(stmt.value, NumberLiteral)
    assert stmt.value.value == 1.0


def test_parse_string_assignment():
    ast = parse_formula("X.192 := 'Token received';")
    assert ast.valid
    stmt = ast.script.statements[0]
    assert isinstance(stmt, AssignStmt)
    assert isinstance(stmt.value, StringLiteral)
    assert stmt.value.value == "Token received"


def test_parse_multiple_statements():
    ast = parse_formula("X.1 := 10; X.2 := 20; X.3 := 30;")
    assert ast.valid
    assert len(ast.script.statements) == 3


# -- Expressions -------------------------------------------------------------


def test_parse_arithmetic():
    ast = parse_formula("X.1 := (a + b) * c / d - e;")
    assert ast.valid
    stmt = ast.script.statements[0]
    assert isinstance(stmt, AssignStmt)
    assert isinstance(stmt.value, BinaryOp)
    assert stmt.value.op == "-"


def test_parse_comparison():
    ast = parse_formula("X.1 := a == b;")
    assert ast.valid
    stmt = ast.script.statements[0]
    assert isinstance(stmt, AssignStmt)
    assert isinstance(stmt.value, BinaryOp)
    assert stmt.value.op == "=="


def test_parse_logical_and():
    ast = parse_formula("X.1 := a && b;")
    assert ast.valid
    stmt = ast.script.statements[0]
    assert isinstance(stmt, AssignStmt)
    assert isinstance(stmt.value, BinaryOp)
    assert stmt.value.op == "&&"


def test_parse_unary_minus():
    ast = parse_formula("X.1 := -5;")
    assert ast.valid
    stmt = ast.script.statements[0]
    assert isinstance(stmt, AssignStmt)
    assert isinstance(stmt.value, UnaryOp)
    assert stmt.value.op == "-"


# -- Paths -------------------------------------------------------------------


def test_parse_dollar_path():
    ast = parse_formula("X.1 := $.GPARAM.ACCESSTOKEN;")
    assert ast.valid
    stmt = ast.script.statements[0]
    assert isinstance(stmt, AssignStmt)
    assert isinstance(stmt.value, PathAccess)
    assert stmt.value.parts == ["$", "GPARAM", "ACCESSTOKEN"]


def test_parse_alias_path():
    ast = parse_formula("X.1 := GETTOKEN.VALUE.token_type;")
    assert ast.valid
    stmt = ast.script.statements[0]
    assert isinstance(stmt, AssignStmt)
    assert isinstance(stmt.value, PathAccess)
    assert stmt.value.parts == ["GETTOKEN", "VALUE", "token_type"]


def test_parse_config_index():
    ast = parse_formula("X.1 := $.CONFIG.0;")
    assert ast.valid
    stmt = ast.script.statements[0]
    assert isinstance(stmt, AssignStmt)
    assert isinstance(stmt.value, PathAccess)
    assert stmt.value.parts == ["$", "CONFIG", "0"]


def test_parse_array_index():
    ast = parse_formula("X.1 := GETFUTUREVIEW.VALUE.value[0].subject;")
    assert ast.valid
    stmt = ast.script.statements[0]
    assert isinstance(stmt, AssignStmt)


# -- Function calls ----------------------------------------------------------


def test_parse_function_call():
    ast = parse_formula("DEBUG(X.1);")
    assert ast.valid
    stmt = ast.script.statements[0]
    assert isinstance(stmt, ExprStmt)
    assert isinstance(stmt.expr, FunctionCall)
    assert stmt.expr.name == "DEBUG"
    assert len(stmt.expr.args) == 1


def test_parse_multi_arg_function():
    ast = parse_formula("X.1 := CONCAT(a, b, c);")
    assert ast.valid
    stmt = ast.script.statements[0]
    assert isinstance(stmt, AssignStmt)
    assert isinstance(stmt.value, FunctionCall)
    assert stmt.value.name == "CONCAT"
    assert len(stmt.value.args) == 3


def test_parse_isequal():
    ast = parse_formula("X.1 := ISEQUAL($.GPARAM.VERBOSE, 'ON');")
    assert ast.valid
    stmt = ast.script.statements[0]
    assert isinstance(stmt, AssignStmt)
    assert isinstance(stmt.value, FunctionCall)
    assert stmt.value.name == "ISEQUAL"


# -- Control flow ------------------------------------------------------------


def test_parse_simple_if():
    ast = parse_formula("IF X.50 THEN X.60 := 0; ENDIF;")
    assert ast.valid
    stmt = ast.script.statements[0]
    assert isinstance(stmt, IfStmt)
    assert len(stmt.then_body) == 1
    assert len(stmt.else_body) == 0


def test_parse_if_else():
    ast = parse_formula("IF X.50 THEN X.60 := 0; ELSE X.60 := 1; ENDIF;")
    assert ast.valid
    stmt = ast.script.statements[0]
    assert isinstance(stmt, IfStmt)
    assert len(stmt.then_body) == 1
    assert len(stmt.else_body) == 1


def test_parse_if_elseif_else():
    ast = parse_formula(
        "IF X.0 > 100 THEN X.1 := 1; ELSE IF X.0 > 10 THEN X.1 := 2; ELSE X.1 := 3; ENDIF;"
    )
    assert ast.valid
    stmt = ast.script.statements[0]
    assert isinstance(stmt, IfStmt)
    assert len(stmt.then_body) == 1
    assert len(stmt.elseif_clauses) == 1
    assert len(stmt.else_body) == 1


def test_parse_multi_elseif_cascade():
    """Test the Daikin-style 5-level ELSE IF cascade with single ENDIF."""
    ast = parse_formula(
        "IF a == 1 THEN X.1 := 1; "
        "ELSE IF a == 2 THEN X.1 := 2; "
        "ELSE IF a == 3 THEN X.1 := 3; "
        "ELSE IF a == 4 THEN X.1 := 4; "
        "ELSE X.1 := 0; ENDIF;"
    )
    assert ast.valid
    stmt = ast.script.statements[0]
    assert isinstance(stmt, IfStmt)
    assert len(stmt.elseif_clauses) == 3
    assert len(stmt.else_body) == 1


# -- Real pilot DDF formulas ------------------------------------------------


def test_parse_ms_calendar_gettoken_formula():
    """Parse the GETTOKEN response formula from Microsoft Calendar DDF."""
    formula = (
        "IF (GETTOKEN.HTTP_CODE==200) && ISEQUAL(GETTOKEN.VALUE.token_type,'Bearer') THEN\n"
        "    X.192 := 'Token received';\n"
        "    X.201 := 1;\n"
        "    $.GPARAM.TOKENTYPE := GETTOKEN.VALUE.token_type;\n"
        "    $.GPARAM.EXPIRESIN := GETTOKEN.VALUE.expires_in;\n"
        "    $.GPARAM.ACCESSTOKEN := GETTOKEN.VALUE.access_token;\n"
        "    $.GPARAM.EXPIRESDATE := ( ( $.GPARAM.EXPIRESIN * 5 ) / 6 ) + $.SYS.TIME;\n"
        "ELSE\n"
        "    $.GPARAM.EXPIRESDATE := 60 + $.SYS.TIME;\n"
        "    X.192 := GETTOKEN.VALUE.error;\n"
        "    X.201 := 0;\n"
        "ENDIF;\n"
        "IF ( LEN(X.192) == 0 ) THEN\n"
        "    X.192 := 'Token Error';\n"
        "ENDIF;\n"
        "GETTOKEN.F := 0;"
    )
    ast = parse_formula(formula)
    assert ast.valid, f"Parse error: {ast.error}"
    assert ast.script is not None
    # Should have: IF/ELSE/ENDIF, IF/ENDIF, assignment
    assert len(ast.script.statements) == 3
    assert isinstance(ast.script.statements[0], IfStmt)
    assert isinstance(ast.script.statements[1], IfStmt)
    assert isinstance(ast.script.statements[2], AssignStmt)


def test_parse_daikin_getdata_small_fragment():
    """Parse a fragment of the Daikin GETDATA formula (the ELSE IF cascade)."""
    formula = (
        "IF (GETDATA.HTTP_CODE == 200) && ISEQUAL(GETDATA.VALUE.managementPoints[1].operationMode.value,'auto') THEN\n"
        "    X.40 := GETDATA.VALUE.managementPoints[1].temperatureControl.value.operationModes.auto.setpoints.roomTemperature.value;\n"
        "ELSE IF (GETDATA.HTTP_CODE == 200) && ISEQUAL(GETDATA.VALUE.managementPoints[1].operationMode.value,'cooling') THEN\n"
        "    X.40 := GETDATA.VALUE.managementPoints[1].temperatureControl.value.operationModes.cooling.setpoints.roomTemperature.value;\n"
        "ELSE IF (GETDATA.HTTP_CODE == 200) && ISEQUAL(GETDATA.VALUE.managementPoints[1].operationMode.value,'heating') THEN\n"
        "    X.40 := GETDATA.VALUE.managementPoints[1].temperatureControl.value.operationModes.heating.setpoints.roomTemperature.value;\n"
        "ENDIF;"
    )
    ast = parse_formula(formula)
    assert ast.valid, f"Parse error: {ast.error}"
    stmt = ast.script.statements[0]
    assert isinstance(stmt, IfStmt)
    assert len(stmt.elseif_clauses) == 2


def test_parse_ms_calendar_rformula_with_date():
    """Parse the timer RFORMULA with date operations."""
    formula = (
        "EVENTREFRESHDATE := DEC($.SYS.TIME, 300) * 300 + 310;\n"
        "EVENTREFRESHDATE_STR := DATE(EVENTREFRESHDATE);\n"
        "X.181 := SUBSTRING(EVENTREFRESHDATE_STR,11,8);"
    )
    ast = parse_formula(formula)
    assert ast.valid, f"Parse error: {ast.error}"
    assert len(ast.script.statements) == 3


def test_parse_trigger_flag():
    """Parse trigger flag assignments."""
    ast = parse_formula("GETTOKEN.F := 1;")
    assert ast.valid
    stmt = ast.script.statements[0]
    assert isinstance(stmt, AssignStmt)
    assert isinstance(stmt.target, PathAccess)
    assert stmt.target.parts == ["GETTOKEN", "F"]


# -- Edge cases --------------------------------------------------------------


def test_parse_oversized_formula():
    ast = parse_formula("X" * 70000)  # 64KB limit
    assert not ast.valid
    assert "exceeds" in (ast.error or "")


def test_parse_empty_formula():
    ast = parse_formula("")
    assert ast.valid
    assert ast.script is not None
    assert len(ast.script.statements) == 0


def test_evaluate_raises_not_implemented():
    with pytest.raises(NotImplementedError, match="Sprint 1"):
        evaluate("X := 1;")


def test_unsupported_formula_error():
    err = UnsupportedFormulaError("ARRAY.MAX")
    assert "ARRAY.MAX" in str(err)
    assert "formula-coverage.md" in str(err)


def test_str_representation():
    ast = parse_formula("X.1 := 1; X.2 := 2;")
    assert "statements=2" in str(ast)

    ast_err = parse_formula("X" * 70000)
    assert "valid=False" in str(ast_err)
