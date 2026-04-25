# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- Project scaffolding: pyproject.toml, CI, Dockerfile, pre-commit
- DDF parser: lexer + parser for CSV-based DDF files
- DDF linter: rule-based validation (DDF001-DDF010)
- Formula engine: lexer + parser (execution deferred to Sprint 1)
- Signing: ECDSA-SHA384 test-key generation, signing, verification
- CLI: `ddf` command with parse, validate, lint, formula, sign, verify, keygen subcommands
- Pilot DDF fixtures: Microsoft Calendar, Daikin Stylish
