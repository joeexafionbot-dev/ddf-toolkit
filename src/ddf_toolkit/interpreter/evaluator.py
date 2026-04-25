"""Tree-walking interpreter for the DDF formula scripting language.

Walks the AST produced by formula/parser.py and executes it against
an Environment instance. No eval(), no exec(), no compile().
"""

from __future__ import annotations

import threading
from typing import Any

from ddf_toolkit.formula.ast import (
    AssignStmt,
    BinaryOp,
    Expression,
    ExprStmt,
    FunctionCall,
    Identifier,
    IfStmt,
    IndexAccess,
    NumberLiteral,
    PathAccess,
    ScriptBlock,
    Statement,
    StringLiteral,
    UnaryOp,
)
from ddf_toolkit.interpreter.environment import Environment

# Limits
MAX_STRING_SIZE = 1_048_576  # 1 MB
DEFAULT_TIMEOUT = 5.0  # seconds


class ExecutionTimeoutError(Exception):
    pass


class ExecutionError(Exception):
    pass


class Interpreter:
    """Tree-walking DDF script interpreter."""

    def __init__(self, env: Environment, timeout: float = DEFAULT_TIMEOUT) -> None:
        self.env = env
        self.timeout = timeout
        self._step_count = 0
        self._max_steps = 100_000

    def execute_script(self, script: ScriptBlock) -> None:
        """Execute a complete script block with timeout."""
        self._step_count = 0

        if self.timeout > 0:
            timer = threading.Timer(self.timeout, self._timeout_handler)
            timer.daemon = True
            timer.start()
            try:
                self._exec_block(script.statements)
            finally:
                timer.cancel()
        else:
            self._exec_block(script.statements)

    def _timeout_handler(self) -> None:
        self._max_steps = 0  # Force step limit to trigger

    def _check_step(self) -> None:
        self._step_count += 1
        if self._step_count > self._max_steps:
            msg = f"Execution exceeded {self._max_steps} steps (possible infinite loop)"
            raise ExecutionTimeoutError(msg)

    # -- Statement execution -------------------------------------------------

    def _exec_block(self, stmts: list[Statement]) -> None:
        for stmt in stmts:
            self._check_step()
            self._exec_stmt(stmt)

    def _exec_stmt(self, stmt: Statement) -> None:
        if isinstance(stmt, AssignStmt):
            self._exec_assign(stmt)
        elif isinstance(stmt, IfStmt):
            self._exec_if(stmt)
        elif isinstance(stmt, ExprStmt):
            self._eval(stmt.expr)
        else:
            msg = f"Unknown statement type: {type(stmt).__name__}"
            raise ExecutionError(msg)

    def _exec_assign(self, stmt: AssignStmt) -> None:
        value = self._eval(stmt.value)
        path = self._resolve_path(stmt.target)
        self.env.set_var(path, value)

    def _exec_if(self, stmt: IfStmt) -> None:
        if self._truthy(self._eval(stmt.condition)):
            self._exec_block(stmt.then_body)
            return

        for clause in stmt.elseif_clauses:
            if self._truthy(self._eval(clause.condition)):
                self._exec_block(clause.body)
                return

        if stmt.else_body:
            self._exec_block(stmt.else_body)

    # -- Expression evaluation -----------------------------------------------

    def _eval(self, expr: Expression) -> Any:
        self._check_step()

        if isinstance(expr, NumberLiteral):
            return expr.value

        if isinstance(expr, StringLiteral):
            return expr.value

        if isinstance(expr, Identifier):
            return self.env.get_var([expr.name])

        if isinstance(expr, PathAccess):
            return self.env.get_var(expr.parts)

        if isinstance(expr, IndexAccess):
            return self._eval_index(expr)

        if isinstance(expr, BinaryOp):
            return self._eval_binary(expr)

        if isinstance(expr, UnaryOp):
            return self._eval_unary(expr)

        if isinstance(expr, FunctionCall):
            return self._eval_function(expr)

        msg = f"Unknown expression type: {type(expr).__name__}"
        raise ExecutionError(msg)

    def _eval_index(self, expr: IndexAccess) -> Any:
        target = self._eval(expr.target)
        index = self._eval(expr.index)
        if isinstance(target, (list, dict)):
            try:
                if isinstance(target, list):
                    return target[int(index)]
                return target[index]
            except (IndexError, KeyError, ValueError, TypeError):
                return None
        return None

    def _eval_binary(self, expr: BinaryOp) -> Any:
        # Special case: dot operator for post-index path continuation
        if expr.op == ".":
            left = self._eval(expr.left)
            if isinstance(expr.right, Identifier):
                key = expr.right.name
                if isinstance(left, dict):
                    return left.get(key)
            return None

        left = self._eval(expr.left)
        right = self._eval(expr.right)

        # Arithmetic
        if expr.op == "+":
            if isinstance(left, str) or isinstance(right, str):
                result = str(left) + str(right)
                if len(result) > MAX_STRING_SIZE:
                    msg = f"String concatenation exceeds {MAX_STRING_SIZE} bytes"
                    raise ExecutionError(msg)
                return result
            return self._num(left) + self._num(right)
        if expr.op == "-":
            return self._num(left) - self._num(right)
        if expr.op == "*":
            return self._num(left) * self._num(right)
        if expr.op == "/":
            r = self._num(right)
            if r == 0:
                return 0
            return self._num(left) / r

        # Comparison
        if expr.op == "==":
            return 1 if left == right else 0
        if expr.op == "!=":
            return 1 if left != right else 0
        if expr.op == "<":
            return 1 if self._num(left) < self._num(right) else 0
        if expr.op == ">":
            return 1 if self._num(left) > self._num(right) else 0
        if expr.op == "<=":
            return 1 if self._num(left) <= self._num(right) else 0
        if expr.op == ">=":
            return 1 if self._num(left) >= self._num(right) else 0

        # Logical
        if expr.op == "&&":
            return 1 if self._truthy(left) and self._truthy(right) else 0

        msg = f"Unsupported binary operator: {expr.op}"
        raise ExecutionError(msg)

    def _eval_unary(self, expr: UnaryOp) -> Any:
        operand = self._eval(expr.operand)
        if expr.op == "-":
            return -self._num(operand)
        msg = f"Unsupported unary operator: {expr.op}"
        raise ExecutionError(msg)

    def _eval_function(self, expr: FunctionCall) -> Any:
        name = expr.name.upper()
        args = [self._eval(a) for a in expr.args]

        # String functions
        if name == "LEN":
            return len(str(args[0])) if args else 0

        if name == "ISEQUAL":
            if len(args) >= 3:
                return 1 if str(args[0])[: int(args[2])] == str(args[1])[: int(args[2])] else 0
            return 1 if str(args[0]) == str(args[1]) else 0

        if name == "CONCAT":
            result = "".join(str(a) for a in args)
            if len(result) > MAX_STRING_SIZE:
                msg = f"CONCAT result exceeds {MAX_STRING_SIZE} bytes"
                raise ExecutionError(msg)
            return result

        if name == "SUBSTRING":
            s = str(args[0])
            start = int(args[1]) if len(args) > 1 else 0
            length = int(args[2]) if len(args) > 2 else len(s) - start
            return s[start : start + length]

        if name == "REPLACEWITHASCII":
            text = str(args[0])
            search = str(args[1])
            ascii_char = chr(int(args[2]))
            return text.replace(search, ascii_char)

        if name == "DECIMAL_TO_STRING" or name == "FLOAT_TO_STRING":
            return str(args[0]) if args else ""

        # Math functions
        if name == "DEC":
            if len(args) >= 2:
                divisor = self._num(args[1])
                if divisor == 0:
                    return 0
                return int(self._num(args[0]) / divisor)
            return int(self._num(args[0]))

        # Date/Time functions
        if name == "DATE":
            import datetime

            ts = self._num(args[0]) if args else self.env.now()
            try:
                dt = datetime.datetime.fromtimestamp(ts, tz=datetime.UTC)
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            except (OSError, ValueError, OverflowError):
                return ""

        if name in (
            "DATE_YEAR",
            "DATEYEAR",
            "DATE_MONTH",
            "DATEMONTH",
            "DATE_DAY",
            "DATEDAY",
            "DATE_HOUR",
            "DATE_MIN",
            "DATE_SEC",
            "DATE_WDAY",
            "DATE_YDAY",
        ):
            return self._eval_date_func(name, args)

        if name == "TIMEFROM_DATE" or name == "TIME_FROM_DATE":
            return self._eval_time_from_date(args)

        if name == "ISO8601":
            return self._eval_iso8601(args)

        # Side-effect functions
        if name == "DEBUG":
            self.env.debug(*args)
            return None

        if name == "SAVE_JSON":
            self.env.save_json(*args)
            return None

        if name == "RANDOMSTRING":
            length = int(args[0]) if args else 10
            return self.env.random_string(length)

        if name == "SYSTEMINFO":
            key = str(args[0]) if args else ""
            return self.env.system_info(key)

        msg = f"Unknown function: {name}"
        raise ExecutionError(msg)

    # -- Date helpers --------------------------------------------------------

    def _eval_date_func(self, name: str, args: list[Any]) -> int:
        import datetime

        ts = self._num(args[0]) if args else self.env.now()
        try:
            dt = datetime.datetime.fromtimestamp(ts, tz=datetime.UTC)
        except (OSError, ValueError, OverflowError):
            return 0

        name_upper = name.upper().replace("_", "")
        if "YEAR" in name_upper:
            return dt.year
        if "MONTH" in name_upper:
            return dt.month
        if "DAY" in name_upper and "YDAY" not in name_upper and "WDAY" not in name_upper:
            return dt.day
        if "HOUR" in name_upper:
            return dt.hour
        if "MIN" in name_upper:
            return dt.minute
        if "SEC" in name_upper:
            return dt.second
        if "WDAY" in name_upper:
            return dt.weekday()
        if "YDAY" in name_upper:
            return dt.timetuple().tm_yday
        return 0

    def _eval_time_from_date(self, args: list[Any]) -> float:
        import datetime

        if len(args) >= 6:
            y, m, d, h, mi, s = (int(a) for a in args[:6])
            dt = datetime.datetime(y, m, d, h, mi, s, tzinfo=datetime.UTC)
        elif len(args) >= 3:
            y, m, d = (int(a) for a in args[:3])
            dt = datetime.datetime(y, m, d, tzinfo=datetime.UTC)
        else:
            return 0
        return dt.timestamp()

    def _eval_iso8601(self, args: list[Any]) -> str:
        import datetime

        ts = self._num(args[0]) if args else self.env.now()
        fmt_type = int(args[1]) if len(args) > 1 else 0
        try:
            dt = datetime.datetime.fromtimestamp(ts, tz=datetime.UTC)
            if fmt_type == 1:
                return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            return dt.strftime("%Y-%m-%dT%H:%M:%S")
        except (OSError, ValueError, OverflowError):
            return ""

    # -- Helpers -------------------------------------------------------------

    def _resolve_path(self, expr: Expression) -> list[str]:
        """Convert an expression used as assignment target to a path list."""
        if isinstance(expr, PathAccess):
            return list(expr.parts)
        if isinstance(expr, Identifier):
            return [expr.name]
        if isinstance(expr, BinaryOp) and expr.op == ".":
            left = self._resolve_path(expr.left)
            right = self._resolve_path(expr.right)
            return left + right
        return [str(expr)]

    @staticmethod
    def _num(val: Any) -> float:
        """Coerce a value to a number."""
        if val is None:
            return 0.0
        if isinstance(val, (int, float)):
            return float(val)
        if isinstance(val, str):
            try:
                return float(val)
            except ValueError:
                return 0.0
        if isinstance(val, bool):
            return 1.0 if val else 0.0
        return 0.0

    @staticmethod
    def _truthy(val: Any) -> bool:
        """DDF truthiness: 0, empty string, None, False are falsy."""
        if val is None:
            return False
        if isinstance(val, (int, float)):
            return val != 0
        if isinstance(val, str):
            return len(val) > 0
        if isinstance(val, bool):
            return val
        return bool(val)
