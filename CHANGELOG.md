# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.3.0] — 2026-04-26

Sprint 2 release — HA-Bridge DDF Generator.

### Added
- **HA-Bridge Generator**: generate DDFs from Home Assistant entities
  - 10 domain templates: switch, sensor, binary_sensor, lock, light, cover, fan, climate, media_player, vacuum
  - HA Source Adapter: live REST API + JSON snapshot backends
  - Integration Grouper: group by (manufacturer, model), 25-item split
  - DDF Builder: compose templates into complete DDFs with standard sections
  - String-vs-Enum mapping for closed-domain states (HVAC modes, lock states, etc.)
- **AST → CSV Serializer**: round-trip DDF serialization
- **Round-Trip Pipeline**: 5-stage validation (serialize → reparse → lint → simulate → sign)
  - Every generated DDF validated before emission
  - RoundTripReport with per-stage pass/fail
- **Snapshot Anonymizer**: strip PII from HA snapshots
  - Deterministic pseudonyms (per-snapshot seed)
  - `--verify` mode with allowlist checking
- **CLI**: `ddf bridge generate`, `ddf bridge inspect`, `ddf bridge coverage`
- **Docs**: bridge.md, bridge-templates.md (per-domain documentation)
- 321 tests, 85% coverage

## [0.2.0] — 2026-04-25

Sprint 1 release — interpreter + simulator.

### Added
- **Interpreter**: Tree-walking DDF script evaluator
  - All pilot-DDF operators: arithmetic, comparison, logical (&&), string, date/time, math
  - Environment abstraction with $.GPARAM, $.SYS, $.CONFIG, $.PARAM, X.n state
  - Side-effect capture: DEBUG, SAVE_JSON, RANDOMSTRING, SYSTEMINFO
  - Sandboxing: step limit, timeout, string cap
- **Formula Parser**: Complete rebuild — recursive-descent with typed AST
  - AST nodes: AssignStmt, IfStmt, ElseIfClause, BinaryOp, FunctionCall, PathAccess
  - Operator precedence, ELSE IF cascade support
- **Simulator**: HAR-based simulation runner
  - HAR 1.2 loader with exact and relaxed URL matching
  - Trigger-flag state machine (RFORMULA → .F flag → *WRITE → response formula)
  - SimulationResult with items, gparams, HTTP log, debug log
- **Golden Harness**: Compare simulation results against expected output
  - Field-level diffs with path reporting
  - Filesystem-based fixture discovery
  - Ignore-fields support for non-deterministic data
- **6 synthetic HAR fixtures**: 3 Microsoft Calendar + 3 Daikin Stylish
- **CLI**: `ddf simulate` now functional (was stub in v0.1.0)
- **Docs**: interpreter.md, simulator.md, captures-research.md
- **Claude Code Review**: GitHub Action for supplementary AI PR review

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
