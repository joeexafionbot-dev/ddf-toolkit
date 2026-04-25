"""Formula evaluator — Sprint 0 stub.

Full tree-walking interpreter is planned for Sprint 1.
See: https://github.com/joeexafionbot-dev/ddf-toolkit/issues/1
"""

from __future__ import annotations

from typing import Any


class UnsupportedFormulaError(NotImplementedError):
    """Raised when a formula operator is not yet supported."""

    def __init__(self, operator: str) -> None:
        super().__init__(
            f"Operator '{operator}' is not yet supported. "
            "See docs/formula-coverage.md for the operator support matrix. "
            "Full execution is planned for Sprint 1."
        )


def evaluate(source: str, context: dict[str, Any] | None = None) -> Any:
    """Evaluate a DDF formula. NOT YET IMPLEMENTED."""
    raise NotImplementedError(
        "Formula execution is not yet implemented (Sprint 1). "
        "Use ddf_toolkit.formula.parse_formula() for syntax validation."
    )
