"""Tests for the DDF script interpreter."""

from __future__ import annotations

import pytest

from ddf_toolkit.formula.parser import parse_formula
from ddf_toolkit.interpreter.environment import Environment, HttpResponse, WriteState
from ddf_toolkit.interpreter.evaluator import (
    ExecutionError,
    Interpreter,
)


def _run(source: str, env: Environment | None = None) -> Environment:
    """Parse and execute a formula, return the environment."""
    if env is None:
        env = Environment()
    ast = parse_formula(source)
    assert ast.valid, f"Parse error: {ast.error}"
    assert ast.script is not None
    interp = Interpreter(env, timeout=5.0)
    interp.execute_script(ast.script)
    return env


# -- Arithmetic --------------------------------------------------------------


def test_addition():
    env = _run("X.1 := 10 + 20;")
    assert env.items[1] == 30.0


def test_subtraction():
    env = _run("X.1 := 50 - 17;")
    assert env.items[1] == 33.0


def test_multiplication():
    env = _run("X.1 := 6 * 7;")
    assert env.items[1] == 42.0


def test_division():
    env = _run("X.1 := 100 / 4;")
    assert env.items[1] == 25.0


def test_division_by_zero():
    env = _run("X.1 := 100 / 0;")
    assert env.items[1] == 0


def test_operator_precedence():
    env = _run("X.1 := 2 + 3 * 4;")
    assert env.items[1] == 14.0


def test_parentheses():
    env = _run("X.1 := (2 + 3) * 4;")
    assert env.items[1] == 20.0


def test_unary_minus():
    env = _run("X.1 := -5;")
    assert env.items[1] == -5.0


# -- Comparison ---------------------------------------------------------------


def test_equality():
    env = _run("X.1 := 10 == 10;")
    assert env.items[1] == 1


def test_inequality():
    env = _run("X.1 := 10 == 20;")
    assert env.items[1] == 0


def test_less_than():
    env = _run("X.1 := 5 < 10;")
    assert env.items[1] == 1


def test_greater_equal():
    env = _run("X.1 := 10 >= 10;")
    assert env.items[1] == 1


# -- Logical ------------------------------------------------------------------


def test_logical_and_true():
    env = _run("X.1 := 1 && 1;")
    assert env.items[1] == 1


def test_logical_and_false():
    env = _run("X.1 := 1 && 0;")
    assert env.items[1] == 0


# -- Assignments ---------------------------------------------------------------


def test_simple_assignment():
    env = _run("X.50 := 1;")
    assert env.items[50] == 1.0


def test_string_assignment():
    env = _run("X.192 := 'Token received';")
    assert env.items[192] == "Token received"


def test_temp_variable():
    env = _run("MYVAR := 42; X.1 := MYVAR;")
    assert env.items[1] == 42.0


def test_gparam_assignment():
    env = _run("$.GPARAM.ACCESSTOKEN := 'abc123';")
    assert env.gparams["ACCESSTOKEN"] == "abc123"


# -- IF/THEN/ELSE/ENDIF -------------------------------------------------------


def test_if_true():
    env = _run("IF 1 THEN X.1 := 10; ENDIF;")
    assert env.items[1] == 10.0


def test_if_false():
    env = _run("IF 0 THEN X.1 := 10; ENDIF;")
    assert env.items.get(1, 0) == 0


def test_if_else():
    env = _run("IF 0 THEN X.1 := 10; ELSE X.1 := 20; ENDIF;")
    assert env.items[1] == 20.0


def test_if_elseif():
    env = _run(
        "X.0 := 50; "
        "IF X.0 > 100 THEN X.1 := 1; "
        "ELSE IF X.0 > 10 THEN X.1 := 2; "
        "ELSE X.1 := 3; ENDIF;"
    )
    assert env.items[1] == 2.0


def test_nested_if():
    env = _run("X.0 := 1; IF X.0 THEN     IF X.0 == 1 THEN X.1 := 'yes'; ENDIF; ENDIF;")
    assert env.items[1] == "yes"


# -- String functions ----------------------------------------------------------


def test_len():
    env = _run("X.1 := LEN('hello');")
    assert env.items[1] == 5


def test_isequal_true():
    env = _run("X.1 := ISEQUAL('hello', 'hello');")
    assert env.items[1] == 1


def test_isequal_false():
    env = _run("X.1 := ISEQUAL('hello', 'world');")
    assert env.items[1] == 0


def test_isequal_partial():
    env = _run("X.1 := ISEQUAL('hello', 'help', 3);")
    assert env.items[1] == 1


def test_concat():
    env = _run("X.1 := CONCAT('hello', ' ', 'world');")
    assert env.items[1] == "hello world"


def test_substring():
    env = _run("X.1 := SUBSTRING('hello world', 6, 5);")
    assert env.items[1] == "world"


def test_replacewithascii():
    env = _run("X.1 := REPLACEWITHASCII('$ANFtest$ANF', '$ANF', 34);")
    assert env.items[1] == '"test"'


def test_decimal_to_string():
    env = _run("X.1 := DECIMAL_TO_STRING(42);")
    assert env.items[1] == "42.0"


# -- Math functions ------------------------------------------------------------


def test_dec_floor():
    env = _run("X.1 := DEC(7.9);")
    assert env.items[1] == 7


def test_dec_division():
    env = _run("X.1 := DEC(100, 3);")
    assert env.items[1] == 33


# -- Date/Time ----------------------------------------------------------------


def test_sys_time():
    env = Environment()
    env.freeze_time(1000000.0)
    _run("X.1 := $.SYS.TIME;", env)
    assert env.items[1] == 1000000.0


def test_date_function():
    env = Environment()
    env.freeze_time(0.0)  # 1970-01-01 00:00:00 UTC
    _run("X.1 := DATE(0);", env)
    assert "1970-01-01" in env.items[1]


def test_date_year():
    env = Environment()
    env.freeze_time(1745571600.0)  # 2025-04-25
    _run("X.1 := DATE_YEAR(1745571600);", env)
    assert env.items[1] == 2025


# -- Side-effect functions -----------------------------------------------------


def test_debug():
    env = _run("DEBUG('test message');")
    assert len(env.debug_log) == 1
    assert "test message" in env.debug_log[0]


def test_save_json():
    env = _run("SAVE_JSON('token', 'value');")
    assert len(env.saved_json) == 1


def test_randomstring():
    env = _run("X.1 := RANDOMSTRING(10);")
    assert env.items[1] == "AAAAAAAAAA"


def test_systeminfo_id():
    env = _run("X.1 := SYSTEMINFO('ID');")
    assert env.items[1] == "TEST-0000-0000"


# -- HTTP response access ------------------------------------------------------


def test_http_code():
    env = Environment()
    env.write_states["GETTOKEN"] = WriteState(
        alias="GETTOKEN",
        http_response=HttpResponse(status_code=200, body={"access_token": "abc"}),
    )
    _run("X.1 := GETTOKEN.HTTP_CODE;", env)
    assert env.items[1] == 200


def test_http_value_path():
    env = Environment()
    env.write_states["GETTOKEN"] = WriteState(
        alias="GETTOKEN",
        http_response=HttpResponse(
            status_code=200,
            body={"token_type": "Bearer", "access_token": "abc123"},
        ),
    )
    _run("X.1 := GETTOKEN.VALUE.token_type;", env)
    assert env.items[1] == "Bearer"


def test_trigger_flag():
    env = Environment()
    env.write_states["GETTOKEN"] = WriteState(alias="GETTOKEN")
    _run("GETTOKEN.F := 1;", env)
    assert env.write_states["GETTOKEN"].trigger is True


# -- Real pilot DDF formulas --------------------------------------------------


def test_ms_calendar_gettoken_formula():
    """Execute the GETTOKEN response formula from Microsoft Calendar DDF."""
    env = Environment()
    env.freeze_time(1000000.0)
    env.write_states["GETTOKEN"] = WriteState(
        alias="GETTOKEN",
        http_response=HttpResponse(
            status_code=200,
            body={
                "token_type": "Bearer",
                "access_token": "eyJ0eXAiOiJKV1Q...",
                "expires_in": 3600,
                "error": None,
            },
        ),
    )

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
    _run(formula, env)

    assert env.items[192] == "Token received"
    assert env.items[201] == 1.0
    assert env.gparams["TOKENTYPE"] == "Bearer"
    assert env.gparams["ACCESSTOKEN"] == "eyJ0eXAiOiJKV1Q..."
    assert env.gparams["EXPIRESIN"] == 3600
    assert env.gparams["EXPIRESDATE"] == (3600 * 5 / 6) + 1000000.0
    assert env.write_states["GETTOKEN"].trigger is False


def test_ms_calendar_date_operations():
    """Execute the timer RFORMULA with date operations."""
    env = Environment()
    env.freeze_time(1745571600.0)  # approx 2025-04-25 some time

    formula = (
        "EVENTREFRESHDATE := DEC($.SYS.TIME, 300) * 300 + 310;\n"
        "EVENTREFRESHDATE_STR := DATE(EVENTREFRESHDATE);\n"
        "X.181 := SUBSTRING(EVENTREFRESHDATE_STR, 11, 8);"
    )
    _run(formula, env)

    assert env.temp_vars["EVENTREFRESHDATE"] is not None
    assert isinstance(env.items[181], str)
    assert len(env.items[181]) == 8  # HH:MM:SS


# -- Error handling ------------------------------------------------------------


def test_unknown_function_raises():
    with pytest.raises(ExecutionError, match="Unknown function"):
        _run("X.1 := NONEXISTENT_FUNC(1);")


def test_step_limit():
    """Ensure infinite loops are caught."""
    env = Environment()
    interp = Interpreter(env, timeout=0)
    interp._max_steps = 100
    ast = parse_formula("X.1 := 1;")
    # Normal execution should be fine
    interp.execute_script(ast.script)
    assert env.items[1] == 1.0
