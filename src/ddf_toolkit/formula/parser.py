"""Formula parser — tokenizes and parses DDF script formulas into an AST.

Sprint 0 scope: parse + validate only. No execution.
"""

from __future__ import annotations

from dataclasses import dataclass

from ddf_toolkit.formula.lexer import tokenize


@dataclass
class FormulaAST:
    """Minimal AST representation of a parsed formula."""

    source: str
    tokens: int
    valid: bool
    error: str | None = None

    def __str__(self) -> str:
        if self.valid:
            return f"FormulaAST(tokens={self.tokens}, valid=True)"
        return f"FormulaAST(valid=False, error={self.error!r})"


def parse_formula(source: str) -> FormulaAST:
    """Parse a DDF formula string. Returns a FormulaAST with validation result."""
    try:
        tokens = tokenize(source)
        return FormulaAST(source=source, tokens=len(tokens), valid=True)
    except ValueError as e:
        return FormulaAST(source=source, tokens=0, valid=False, error=str(e))
