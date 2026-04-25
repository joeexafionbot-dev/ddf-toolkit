# Roadmap

High-level sprint plan. Only Sprint 0 and Sprint 1 have committed scope.

## Sprint 0 (current) — Core Toolkit
Parse, validate, lint, and sign DDF files. CLI-only, no hardware.

## Sprint 1 — Interpreter + Capture Recorder
- Full DDF script-language interpreter ([#1](https://github.com/joeexafionbot-dev/ddf-toolkit/issues/1))
- HAR-based simulator with mock server ([#2](https://github.com/joeexafionbot-dev/ddf-toolkit/issues/2))
- Capture recorder against real hardware
- Golden-file regression harness

## Sprint 2 — HA-Bridge DDF Generator
- HA-Bridge DDF generator using Sprint 0 linter and Sprint 1 simulator as quality gate

## Sprint 3+ — Composer Web-UI
- Web-based DDF editor/composer
- Visual formula builder

## Phase 1 — Marketplace
- DDF marketplace integration
- Submission and review workflow

## Phase 2 — Extended Protocols
- BACnet support
- OPC-UA support
