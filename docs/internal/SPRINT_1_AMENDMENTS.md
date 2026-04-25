# Sprint 1 PRD — Amendments

**Date:** 2026-04-25
**Context:** Pre-Day-1 review of Sprint 1 PRD against Sprint 0 reality.
**Decision authority:** Martin Mair (ekon GmbH)

---

## 1. Formula Parser: Full Rebuild

**Finding:** Sprint 0 formula "parser" is a tokenizer + `valid: bool`. Sprint 1 requires a real recursive-descent parser with operator precedence, typed AST nodes (AssignStmt, IfStmt, ElseIfClause, FunctionCall, BinaryExpr, PathAccess, Literal), and proper statement blocks.

**Decision:** Complete rebuild of `ddf_toolkit.formula.parser` and new `ddf_toolkit.formula.ast` module. Sprint 0 tokenizer (`lexer.py`) is reused.

## 2. Formula Size Limit: 4KB → 64KB

**Finding:** Daikin GETDATA formula (lines 155-212 of the CSV) exceeds the Sprint 0 4KB limit.

**Decision:** Raise `MAX_FORMULA_SIZE` to 64KB. Real protection comes from the 5s execution timeout and 1MB string concatenation cap.

## 3. Operator Scope: Pilot-Only

**Finding:** PRD §6.1 operator table lists `||`, `!`, `NOT` — these were NOT found in the Sprint 0 operator audit (Issue #5). Only `&&` was found as a logical operator.

**Decision:** `||`, `!`, `NOT` are out of scope for Sprint 1. Marked as "planned (Sprint 2)" in `docs/formula-coverage.md`. Raise `NotImplementedError` if encountered in third-party DDFs.

**Why:** PRD Decision #2 ("full DDF script language as observed in pilot DDFs") takes precedence over the §6.1 table.

## 4. Listener Webhook Fixture Replaced

**Finding:** Microsoft Calendar DDF has no `*LISTENER` section. Fixture #3 (`microsoft_calendar_listener_webhook.har`) cannot be tested against this DDF.

**Decision:** Replace with `microsoft_calendar_token_refresh.har` — token refresh cycle when `$.GPARAM.EXPIRESDATE` expires. Listener tests deferred to Sprint 2 with a DDF that uses `*LISTENER` (Hikvision or Alexa candidates).

## 5. Pilot DDF File Naming

**Finding:** PRD references `microsoft_calendar.csv` and `daikin_stylish.csv`, but actual filenames are vendor-format long names.

**Decision:** Create canonical copies at `tests/fixtures/ddfs/microsoft_calendar.csv` and `daikin_stylish.csv`. Move originals to `tests/fixtures/ddfs/originals/`.

## 6. Time Control: `time-machine`

**Decision:** Use `time-machine` (not `freezegun`). Better C-based time interception for `time.time()` and `datetime.now()`.

## 7. ELSE IF Semantics

**Finding:** Daikin GETDATA formula (lines 178-208) uses `ELSE IF ... ELSE IF ... ENDIF` with a single `ENDIF` closing 5 levels.

**Decision:** `ELSE IF` is syntactic sugar for `ELSE { IF ... }` with implicit ENDIF collapse. In the AST, model as `ElseIfClause` (not nested `IfStmt`) to preserve original formatting in pretty-printing.

## 8. $.PARAM vs $.GPARAM

**Decision:** Two separate dicts in the Environment.
- `$.GPARAM.*` — main device parameters, persist across the entire simulation
- `$.PARAM.*` — sub-device (slave) parameters, populated per-`*WRITE` via `*ARGS`
- In single-slave test mode: `params` starts empty, filled by ARGS; `gparams` persists

Document in `docs/interpreter.md`.

## 9. SAVE_JSON Semantics

**Decision:** `env.save_json()` writes to an in-memory map (test mode) or JSON file relative to DDF path (production mode). Overwrite, not append. Marked as AMBIGUOUS in `docs/interpreter.md`.

## 10. Claude Code GitHub Action

**Decision:** Use the official Claude GitHub App (installed by Martin via Settings → Integrations). Joe writes the workflow + reviewer prompt. No API key in secrets needed.

**Status:** Waiting for Martin to confirm app installation before writing workflow.

---

## Updated Fixture Plan

| # | Fixture | Change |
|---|---------|--------|
| MS Calendar #1 | `microsoft_calendar_oauth_flow.har` | No change |
| MS Calendar #2 | `microsoft_calendar_event_list.har` | No change |
| MS Calendar #3 | `microsoft_calendar_token_refresh.har` | **Changed** from webhook to token refresh |
| Daikin #1 | `daikin_stylish_status_poll.har` | No change |
| Daikin #2 | `daikin_stylish_set_mode.har` | No change |
| Daikin #3 | `daikin_stylish_error_response.har` | No change |

---

*This document supplements the Sprint 1 PRD. In case of conflict, this document takes precedence.*
