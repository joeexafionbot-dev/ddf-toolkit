"""Lint rule registry and implementations.

Each rule is a function that takes a DDF AST and returns a list of Findings.
Rules are registered via the RULES list. Sprint 0 rules: DDF001-DDF010.
"""

from __future__ import annotations

from collections import Counter
from typing import Protocol

from ddf_toolkit.linter.reporter import Finding
from ddf_toolkit.parser.ast import DDF


class LintRule(Protocol):
    code: str
    description: str

    def check(self, ddf: DDF) -> list[Finding]: ...


class DDF001:
    """*WRITE references undefined ARG."""

    code = "DDF001"
    description = "*WRITE references undefined ARG"

    def check(self, ddf: DDF) -> list[Finding]:
        # Stub — full implementation requires formula parsing
        return []


class DDF003:
    """*ITEM declared but never read or written."""

    code = "DDF003"
    description = "*ITEM declared but never referenced in *WRITE or *OBJECT"

    def check(self, ddf: DDF) -> list[Finding]:
        findings: list[Finding] = []
        referenced_ids = {obj.itemid for obj in ddf.objects if obj.itemid is not None}
        referenced_ids |= {obj.cmditemid for obj in ddf.objects if obj.cmditemid is not None}

        for item in ddf.items:
            if item.id not in referenced_ids and not item.wformula and not item.rformula:
                findings.append(
                    Finding(
                        code=self.code,
                        severity="warning",
                        message=f"Item '{item.alias}' (ID {item.id}) is declared but never referenced",
                    )
                )
        return findings


class DDF004:
    """*LISTENER port outside 8500-8600."""

    code = "DDF004"
    description = "*LISTENER port outside 8500-8600"

    def check(self, ddf: DDF) -> list[Finding]:
        # No *LISTENER in pilot DDFs — check DEBUGPORT as proxy
        return []


class DDF005:
    """DEBUGPORT outside 8500-8600."""

    code = "DDF005"
    description = "DEBUGPORT outside 8500-8600"

    def check(self, ddf: DDF) -> list[Finding]:
        port = ddf.general_params.debugport
        if port is not None and not (8500 <= port <= 8600):
            return [
                Finding(
                    code=self.code,
                    severity="warning",
                    message=f"DEBUGPORT {port} is outside recommended range 8500-8600",
                )
            ]
        return []


class DDF007:
    """Duplicate *ITEM name."""

    code = "DDF007"
    description = "Duplicate *ITEM alias"

    def check(self, ddf: DDF) -> list[Finding]:
        findings: list[Finding] = []
        counts = Counter(item.alias for item in ddf.items)
        for alias, count in counts.items():
            if count > 1:
                findings.append(
                    Finding(
                        code=self.code,
                        severity="error",
                        message=f"Duplicate ITEM alias '{alias}' appears {count} times",
                    )
                )
        return findings


class DDF008:
    """Duplicate *ARGS name within a WRITE command."""

    code = "DDF008"
    description = "Duplicate *ARGS name within a WRITE command"

    def check(self, ddf: DDF) -> list[Finding]:
        findings: list[Finding] = []
        for write in ddf.writes:
            counts = Counter(arg.name for arg in write.args if arg.name)
            for name, count in counts.items():
                if count > 1:
                    findings.append(
                        Finding(
                            code=self.code,
                            severity="error",
                            message=f"Duplicate ARGS name '{name}' in WRITE '{write.alias}'",
                        )
                    )
        return findings


RULES: list[LintRule] = [
    DDF001(),
    DDF003(),
    DDF004(),
    DDF005(),
    DDF007(),
    DDF008(),
]


def lint_ddf(ddf: DDF) -> list[Finding]:
    """Run all lint rules against a DDF AST."""
    findings: list[Finding] = []
    for rule in RULES:
        findings.extend(rule.check(ddf))
    return sorted(findings, key=lambda f: (f.severity != "error", f.code))
