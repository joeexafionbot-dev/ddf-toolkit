"""Lint rule registry and implementations.

Each rule is a class with code, severity, check(ddf) -> list[Finding].
Rules are registered via the RULES list. Sprint 0 rules: DDF001-DDF010.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Protocol

from ddf_toolkit.linter.reporter import Finding
from ddf_toolkit.parser.ast import DDF


class LintRule(Protocol):
    code: str
    description: str

    def check(self, ddf: DDF) -> list[Finding]: ...


def _all_formulas(ddf: DDF) -> list[tuple[str, str]]:
    """Extract all formula strings from a DDF with their locations."""
    formulas: list[tuple[str, str]] = []
    for cmd in ddf.commands:
        if cmd.formula:
            formulas.append((f"COMMAND.{cmd.alias}", cmd.formula))
    for write in ddf.writes:
        if write.formula:
            formulas.append((f"WRITE.{write.alias}", write.formula))
    for item in ddf.items:
        if item.wformula:
            formulas.append((f"ITEM.{item.alias}.WFORMULA", item.wformula))
        if item.rformula:
            formulas.append((f"ITEM.{item.alias}.RFORMULA", item.rformula))
    return formulas


def _all_write_aliases(ddf: DDF) -> set[str]:
    """Get all WRITE command aliases."""
    return {w.alias for w in ddf.writes}


def _all_args_aliases(ddf: DDF) -> dict[str, set[str]]:
    """Get ARGS aliases grouped by parent WRITE alias."""
    result: dict[str, set[str]] = {}
    for write in ddf.writes:
        result[write.alias] = {arg.alias for arg in write.args}
    return result


class DDF001:
    """*WRITE references undefined ARG."""

    code = "DDF001"
    description = "*WRITE references undefined ARG"

    def check(self, ddf: DDF) -> list[Finding]:
        findings: list[Finding] = []
        write_aliases = _all_write_aliases(ddf)
        # Check that ARGS belong to valid parent WRITE aliases
        # Skip header-like values (METHOD, ALIAS, TYPE, NAME, VALUE, ITEM, FORMAT)
        header_values = {"METHOD", "ALIAS", "TYPE", "NAME", "VALUE", "ITEM", "FORMAT"}
        for write in ddf.writes:
            for arg in write.args:
                if (
                    arg.alias
                    and arg.alias.upper() not in header_values
                    and arg.alias not in write_aliases
                ):
                    findings.append(
                        Finding(
                            code=self.code,
                            severity="error",
                            message=(
                                f"ARGS in WRITE '{write.alias}' references "
                                f"unknown alias '{arg.alias}'"
                            ),
                        )
                    )
        return findings


class DDF002:
    """*FORMULA references undefined DATA.x.y."""

    code = "DDF002"
    description = "*FORMULA references undefined DATA path"

    def check(self, ddf: DDF) -> list[Finding]:
        findings: list[Finding] = []
        write_aliases = _all_write_aliases(ddf)
        formulas = _all_formulas(ddf)

        for location, formula in formulas:
            # Find ALIAS.VALUE references where ALIAS is not a known WRITE
            refs = re.findall(r"\b(\w+)\.VALUE\b", formula)
            for ref in refs:
                if ref not in write_aliases and ref != "DATA":
                    findings.append(
                        Finding(
                            code=self.code,
                            severity="warning",
                            message=(
                                f"Formula in {location} references '{ref}.VALUE' "
                                f"but '{ref}' is not a known WRITE alias"
                            ),
                        )
                    )
        return findings


class DDF003:
    """*ITEM declared but never read or written."""

    code = "DDF003"
    description = "*ITEM declared but never referenced in *WRITE, *OBJECT, or formulas"

    def check(self, ddf: DDF) -> list[Finding]:
        findings: list[Finding] = []
        referenced_ids: set[int] = set()

        # Referenced by *OBJECT
        for obj in ddf.objects:
            if obj.itemid is not None:
                referenced_ids.add(obj.itemid)
            if obj.cmditemid is not None:
                referenced_ids.add(obj.cmditemid)

        # Referenced by formulas (X.{ID} pattern)
        formulas = _all_formulas(ddf)
        for _, formula in formulas:
            for match in re.finditer(r"\bX\.(\d+)\b", formula):
                referenced_ids.add(int(match.group(1)))

        for item in ddf.items:
            if item.id not in referenced_ids and not item.wformula and not item.rformula:
                findings.append(
                    Finding(
                        code=self.code,
                        severity="warning",
                        message=(
                            f"Item '{item.alias}' (ID {item.id}) is declared but never referenced"
                        ),
                    )
                )
        return findings


class DDF004:
    """*LISTENER port outside 8500-8600."""

    code = "DDF004"
    description = "*LISTENER port outside 8500-8600"

    def check(self, ddf: DDF) -> list[Finding]:
        # Check LISTENER_PORT in general params extra fields
        listener_port_str = ddf.general_params.extra.get("LISTENER_PORT", "")
        if not listener_port_str:
            return []
        try:
            port = int(listener_port_str)
        except ValueError:
            return [
                Finding(
                    code=self.code,
                    severity="error",
                    message=f"LISTENER_PORT '{listener_port_str}' is not a valid port number",
                )
            ]
        if not (8500 <= port <= 8600):
            return [
                Finding(
                    code=self.code,
                    severity="warning",
                    message=f"LISTENER_PORT {port} is outside recommended range 8500-8600",
                )
            ]
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


class DDF006:
    """MIN_CONTROL_VERSION not parseable as version string."""

    code = "DDF006"
    description = "MIN_CONTROL_VERSION not parseable as version string"

    def check(self, ddf: DDF) -> list[Finding]:
        version = ddf.general_metadata.min_control_version
        if not version:
            return []
        # myGEKKO versions: V{number}-{patch} e.g. V9615-08, V10384-01
        if not re.match(r"^V\d+-\d+$", version):
            return [
                Finding(
                    code=self.code,
                    severity="warning",
                    message=(
                        f"MIN_CONTROL_VERSION '{version}' does not match "
                        f"expected pattern V{{number}}-{{patch}}"
                    ),
                )
            ]
        return []


class DDF007:
    """Duplicate *ITEM alias."""

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


class DDF009:
    """AUTHENTIFICATION = PASSWORD without *CONFIG field for credentials."""

    code = "DDF009"
    description = "AUTHENTIFICATION requires PASSWORD but no CONFIG for credentials"

    def check(self, ddf: DDF) -> list[Finding]:
        auth = ddf.general_params.authentification.upper()
        if auth not in ("PASSWORD", "DEFPASSWORD"):
            return []

        config_aliases = {c.alias.upper() for c in ddf.config}
        # For PASSWORD auth, we need credential config fields or GENERAL params
        has_password = "PASSWORD" in config_aliases or ddf.general_params.extra.get("PASSWORD", "")
        if not has_password and auth == "PASSWORD":
            return [
                Finding(
                    code=self.code,
                    severity="warning",
                    message=(
                        "AUTHENTIFICATION is PASSWORD but no PASSWORD config field "
                        "or GENERAL parameter found"
                    ),
                )
            ]
        return []


class DDF010:
    """*ITEM with formula references unknown source."""

    code = "DDF010"
    description = "*ITEM formula references unknown WRITE alias via .F trigger"

    def check(self, ddf: DDF) -> list[Finding]:
        findings: list[Finding] = []
        write_aliases = _all_write_aliases(ddf)
        command_aliases = {c.alias for c in ddf.commands}
        known_aliases = write_aliases | command_aliases

        for item in ddf.items:
            for formula_name, formula in [
                ("WFORMULA", item.wformula),
                ("RFORMULA", item.rformula),
            ]:
                if not formula:
                    continue
                # Find ALIAS.F := 1 patterns (trigger references)
                for match in re.finditer(r"\b(\w+)\.F\s*:=", formula):
                    alias = match.group(1)
                    if alias not in known_aliases:
                        findings.append(
                            Finding(
                                code=self.code,
                                severity="warning",
                                message=(
                                    f"Item '{item.alias}' {formula_name} triggers "
                                    f"'{alias}.F' but '{alias}' is not a known "
                                    f"WRITE or COMMAND alias"
                                ),
                            )
                        )
        return findings


RULES: list[LintRule] = [
    DDF001(),
    DDF002(),
    DDF003(),
    DDF004(),
    DDF005(),
    DDF006(),
    DDF007(),
    DDF008(),
    DDF009(),
    DDF010(),
]


def lint_ddf(ddf: DDF) -> list[Finding]:
    """Run all lint rules against a DDF AST."""
    findings: list[Finding] = []
    for rule in RULES:
        findings.extend(rule.check(ddf))
    return sorted(findings, key=lambda f: (f.severity != "error", f.code))
