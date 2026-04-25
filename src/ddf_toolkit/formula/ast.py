"""Typed AST nodes for the DDF formula scripting language.

The DDF formula language is an imperative scripting language with:
- Assignments (:=)
- Block IF/THEN/ELSE IF/ELSE/ENDIF
- Function calls (DEBUG, LEN, CONCAT, etc.)
- Path access ($.GPARAM.*, ALIAS.VALUE.*, X.n)
- Arithmetic, comparison, logical operators
"""

from __future__ import annotations

from dataclasses import dataclass, field

# -- Expressions (produce a value) ------------------------------------------


@dataclass(frozen=True)
class NumberLiteral:
    value: float


@dataclass(frozen=True)
class StringLiteral:
    value: str


@dataclass(frozen=True)
class Identifier:
    """Simple name: X, COUNT, TZONE, etc."""

    name: str


@dataclass(frozen=True)
class PathAccess:
    """Dot-separated path: $.GPARAM.ACCESSTOKEN, GETTOKEN.VALUE.token_type, X.192"""

    parts: list[str]

    def __str__(self) -> str:
        return ".".join(self.parts)


@dataclass(frozen=True)
class IndexAccess:
    """Array index: value[0].field"""

    target: Expression
    index: Expression


@dataclass(frozen=True)
class BinaryOp:
    """Binary operation: a + b, a == b, a && b"""

    left: Expression
    op: str
    right: Expression


@dataclass(frozen=True)
class UnaryOp:
    """Unary operation: -x, !x"""

    op: str
    operand: Expression


@dataclass(frozen=True)
class FunctionCall:
    """Function call: DEBUG(x, y), CONCAT(a, b, c)"""

    name: str
    args: list[Expression]


# Union type for all expressions
Expression = (
    NumberLiteral
    | StringLiteral
    | Identifier
    | PathAccess
    | IndexAccess
    | BinaryOp
    | UnaryOp
    | FunctionCall
)


# -- Statements (perform actions) -------------------------------------------


@dataclass(frozen=True)
class AssignStmt:
    """Assignment: X.192 := 'Token received';"""

    target: Expression
    value: Expression


@dataclass(frozen=True)
class ExprStmt:
    """Expression used as statement (e.g., bare function call): DEBUG(x);"""

    expr: Expression


@dataclass
class ElseIfClause:
    """One ELSE IF branch in an if-chain."""

    condition: Expression
    body: list[Statement]


@dataclass
class IfStmt:
    """Block IF/THEN/ELSE IF/ELSE/ENDIF."""

    condition: Expression
    then_body: list[Statement]
    elseif_clauses: list[ElseIfClause] = field(default_factory=list)
    else_body: list[Statement] = field(default_factory=list)


# Union type for all statements
Statement = AssignStmt | ExprStmt | IfStmt


@dataclass
class ScriptBlock:
    """A complete script: list of statements."""

    statements: list[Statement]
    source: str = ""
