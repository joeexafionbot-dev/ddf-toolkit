#!/usr/bin/env python3
"""Audit all formulas in pilot DDFs and report operator/function usage.

Run: python scripts/audit_formulas.py
"""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from ddf_toolkit.formula.lexer import TokenType, tokenize
from ddf_toolkit.parser import parse_ddf

FIXTURES = Path("tests/fixtures/ddfs")


def extract_formulas(ddf_path: Path) -> list[tuple[str, str]]:
    """Extract all formulas from a DDF, returning (location, formula_source) pairs."""
    ddf = parse_ddf(ddf_path)
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


def audit_ddf(ddf_path: Path) -> dict[str, Counter[str]]:
    """Audit a DDF and return operator/function usage counts."""
    formulas = extract_formulas(ddf_path)
    print(f"\n{'='*60}")
    print(f"DDF: {ddf_path.name}")
    print(f"Formulas found: {len(formulas)}")
    print(f"{'='*60}")

    keywords: Counter[str] = Counter()
    operators: Counter[str] = Counter()
    functions: Counter[str] = Counter()
    path_patterns: Counter[str] = Counter()

    # Regex for function calls: IDENTIFIER followed by (
    func_pattern = re.compile(r"\b([A-Z_][A-Z0-9_]*)\s*\(")
    # Regex for path access patterns
    path_pattern = re.compile(
        r"\$\.(SYS|GPARAM|PARAM|CONFIG|SLAVE|ITEMMASK|MOUSE|CTRLVAR)\b"
    )
    data_pattern = re.compile(
        r"\b(\w+)\.(VALUE|ARRAY|ASLIST|FIND|EXIST|HTTP_CODE|HTTP_DATA|URL|F|T|Q|L|P|EC|EN)\b"
    )

    for location, formula in formulas:
        # Tokenize
        try:
            tokens = tokenize(formula)
        except ValueError:
            print(f"  SKIP (too large): {location}")
            continue

        for tok in tokens:
            if tok.type in (
                TokenType.IF, TokenType.THEN, TokenType.ELSE, TokenType.ENDIF,
                TokenType.SWITCH, TokenType.CASE, TokenType.DEFAULT, TokenType.ENDSWITCH,
                TokenType.FOR, TokenType.TO, TokenType.BY, TokenType.DO, TokenType.ENDFOR,
            ):
                keywords[tok.value.upper()] += 1
            elif tok.type in (
                TokenType.ASSIGN, TokenType.EQ, TokenType.NEQ,
                TokenType.LT, TokenType.GT, TokenType.LTE, TokenType.GTE,
                TokenType.AND, TokenType.ANDNOT, TokenType.OR,
                TokenType.BAND, TokenType.BOR, TokenType.BANDNOT,
                TokenType.SHR, TokenType.SHL,
                TokenType.PLUS, TokenType.MINUS, TokenType.STAR, TokenType.SLASH,
                TokenType.CARET,
            ):
                operators[tok.value] += 1

        # Function calls (from raw source)
        for match in func_pattern.finditer(formula):
            func_name = match.group(1)
            # Skip IF, ELSE — they're keywords, not functions
            if func_name not in ("IF", "ELSE", "THEN", "ENDIF", "SWITCH", "CASE", "FOR"):
                functions[func_name] += 1

        # Path access patterns
        for match in path_pattern.finditer(formula):
            path_patterns[f"$.{match.group(1)}"] += 1

        for match in data_pattern.finditer(formula):
            path_patterns[f"ALIAS.{match.group(2)}"] += 1

    return {
        "keywords": keywords,
        "operators": operators,
        "functions": functions,
        "path_patterns": path_patterns,
    }


def main() -> None:
    all_results: dict[str, dict[str, Counter[str]]] = {}

    for ddf_path in sorted(FIXTURES.glob("*.csv")):
        results = audit_ddf(ddf_path)
        all_results[ddf_path.name] = results

        for category, counts in results.items():
            if counts:
                print(f"\n  {category.upper()}:")
                for name, count in counts.most_common():
                    print(f"    {name:30s} {count:4d}")

    # Combined summary
    print(f"\n{'='*60}")
    print("COMBINED SUMMARY — ALL DDFs")
    print(f"{'='*60}")

    combined: dict[str, Counter[str]] = {
        "keywords": Counter(),
        "operators": Counter(),
        "functions": Counter(),
        "path_patterns": Counter(),
    }
    for results in all_results.values():
        for cat, counts in results.items():
            combined[cat] += counts

    for category, counts in combined.items():
        if counts:
            print(f"\n  {category.upper()}:")
            for name, count in counts.most_common():
                print(f"    {name:30s} {count:4d}")


if __name__ == "__main__":
    main()
