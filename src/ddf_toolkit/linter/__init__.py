"""DDF linter — rule-based validation and style checking."""

from __future__ import annotations

from ddf_toolkit.linter.reporter import Finding
from ddf_toolkit.linter.rules import lint_ddf

__all__ = ["Finding", "lint_ddf"]
