# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.1.0] — 2026-04-25

Sprint 0 release — foundational DDF toolkit.

### Added
- **Parser**: CSV lexer + parser producing typed AST from DDF files
  - Handles `*SIGNATURE`, dual `*GENERAL`, inline `*ARGS`, `#`-comments
  - Auto-detect encoding (UTF-8/CP1252) via BOM + chardet
  - Normalizes `*PREPROCESS` → `*READ`, `*ONCHANGE` → `*WRITE`
- **Linter**: 10 rules (DDF001–DDF010) with rule registry pattern
  - Each rule has pass + fail test fixture
  - Both pilot DDFs lint clean (zero errors)
- **Formula engine**: Lexer + parser for DDF script language (parse-only)
  - Tokenizes all operators from DeviceLib.pdf (IF/THEN, SWITCH/CASE, FOR, bitwise)
  - Block comments `/* */` supported
  - Execution stubbed for Sprint 1
- **Signing**: ECDSA-SHA384 test-key generation, signing, verification
  - Round-trip verified on both pilot DDFs
  - Tamper detection tested
- **CLI**: 9 commands via Typer — parse, validate, lint, formula, simulate, sign, verify, keygen, version
  - Color output via rich (auto-disabled on non-TTY / `NO_COLOR`)
  - `--quiet` / `--verbose` flags with observable behavior
  - `--format json` on validate and lint
  - Exit codes: 0 (success), 1 (validation), 2 (usage), 3 (internal)
  - `ddf version` includes git SHA
- **CI/CD**: GitHub Actions (lint + test + build wheel + Docker)
- **Docs**: architecture, ddf-schema (from DeviceLib.pdf), formula-coverage, cli-reference, contributing, roadmap
- **Pilot DDFs**: Microsoft Calendar, Daikin Stylish, Microsoft Shifts (bonus)
- 86 tests, 90% line coverage

### Deferred to Sprint 1
- Formula execution (interpreter)
- HAR-based simulator + golden-file harness
- Synthetic HAR capture fixtures
