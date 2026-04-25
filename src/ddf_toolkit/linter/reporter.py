"""Lint finding data structures and output formatting."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


@dataclass
class Finding:
    code: str
    severity: Literal["error", "warning", "info"]
    message: str
    line: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "line": self.line,
        }
