# Sprint 0 PRD — Amendments

**Date:** 2026-04-25
**Context:** Pre-Day-1 review of pilot DDFs revealed structural differences between PRD assumptions and DDF reality.
**Decision authority:** Martin Mair (ekon GmbH)

---

## 1. Scope Changes

### 1.1 Formula Engine: Parse + Validate only (no execution)

**Finding:** The PRD assumed a functional expression evaluator (`IF(cond, then, else)`). Real DDFs use an imperative scripting language with multi-statement blocks, assignments (`:=`), block `IF/THEN/ELSE IF/ELSE/ENDIF`, side effects (state mutation on `$.GPARAM`, `X.n`, trigger flags like `.F := 1`), and built-in functions (`DEBUG`, `SAVE_JSON`, `SYSTEMINFO`, etc.).

**Decision:** Sprint 0 delivers Lexer + Parser + AST + syntactic validation. Execution is stubbed (`NotImplementedError`). Full interpreter moves to Sprint 1.

**Rationale:** Sprint 0 promise ("read, validate, lint DDFs without hardware") remains intact. The interpreter needs real capture data for validation, which arrives with Sprint 1 (Capture-Recorder).

### 1.2 Simulator: Deferred to Sprint 1

**Finding:** `*READ` sections are empty in both pilot DDFs. All logic runs via `*WRITE` formulas with trigger flags (`.F := 1`). The PRD's simulator design ("execute all `*READ` commands") does not match reality.

**Decision:** Simulator (`ddf_toolkit.simulator`) and golden harness (`ddf_toolkit.golden`) move entirely to Sprint 1. The `simulator/` and `golden/` directories will be created as empty packages with `NotImplementedError` stubs.

**Impact on DoD:** Items 4 (simulate against HAR captures) and 12 (walkthrough runs end-to-end) are adjusted — the walkthrough covers parse, lint, sign/verify but not simulate.

### 1.3 Synthetic HAR Fixtures: Deferred to Sprint 1

**Finding:** Without a working simulator, HAR fixtures have no consumer in Sprint 0.

**Decision:** HAR fixture creation moves to Sprint 1 alongside the simulator. Sprint 0 DoD item 9 (six synthetic HAR fixtures) is deferred.

---

## 2. AST Design Changes

The PRD's AST (Section 6.1) was a prediction. The actual DDF structure differs in six ways:

| # | PRD Assumption | Reality | Decision |
|---|---------------|---------|----------|
| 1 | No `*SIGNATURE` in AST | `*SIGNATURE` is the first section (SIGN_ALGO, SIGN_DATE, FILE_VERDATE, SIGNATURE) | Add `SignatureSection` dataclass |
| 2 | Single `GeneralSection` | `*GENERAL` appears twice: first for device metadata, second for connection/auth parameters | Model as two sub-sections or a single dataclass with both blocks |
| 3 | `args: list[ArgsDef]` as top-level | `*ARGS` are inline under their parent `*WRITE` command | `WriteCommand` contains its own `args: list[ArgsDef]` |
| 4 | `*COMMAND` mentioned but not specified | `*COMMAND` section exists with ID, ALIAS, FORMULA columns | Add `CommandSection` dataclass |
| 5 | `reads: list[ReadCommand]` populated | `*READ` section is empty in both pilots; logic lives in `*WRITE` formulas | Keep `ReadCommand` in AST but expect it to be empty; document pattern |
| 6 | `formulas: list[FormulaDef]` as separate section | No `*FORMULA` section exists; formulas are inline in `*WRITE` (FORMULA column) and `*ITEM` (WFORMULA/RFORMULA columns) | Remove top-level `FormulaDef`; formulas are attributes of their parent sections |

**Guiding principle:** Follow the reality of the DDF files, not the PRD prediction. Document the final AST structure in `docs/architecture.md`.

---

## 3. Terminology and Syntax Corrections

| # | PRD Text | Reality | Decision |
|---|----------|---------|----------|
| 1 | `AUTHENTICATION` | `AUTHENTIFICATION` (both pilot DDFs) | Use DDF spelling as canonical |
| 2 | `#` comment lines not mentioned | Both DDFs use `#` prefix to comment out rows | Lexer skips lines starting with `#` |
| 3 | Encoding assumed UTF-8 | Daikin DDF is CP1252 (broken `C` for `degrees-C`); Calendar is UTF-8 | Auto-detect via BOM + chardet as per PRD Section 6.1 |

---

## 4. Formula Operator Audit (Pre-Sprint-0 Quick Pass)

Operators found across both pilot DDFs (Microsoft Calendar + Daikin Stylish):

### Control Flow
- `IF / THEN / ELSE / ELSE IF / ENDIF` (statement-based, not functional)

### Assignment
- `:=` (variable assignment with side effects)

### Comparison
- `==`, `!=`, `<`, `>`, `<=`, `>=`

### Logical
- `&&` (AND), `||` (OR, not yet observed but likely)

### Arithmetic
- `+`, `-`, `*`, `/`

### Path Access
- `$.GPARAM.*`, `$.SYS.TIME`, `$.CONFIG.*`, `$.PARAM.*`
- `WRITE_ALIAS.VALUE.path.to.field`
- `WRITE_ALIAS.VALUE.path[index].field`
- `WRITE_ALIAS.HTTP_CODE`, `WRITE_ALIAS.HTTP_DATA`, `WRITE_ALIAS.URL`
- `WRITE_ALIAS.T` (timestamp), `WRITE_ALIAS.F` (trigger flag)
- `WRITE_ALIAS.ARRAY.LEN.path`
- `WRITE_ALIAS.ASLIST.path[].field`

### Built-in Functions
- `ISEQUAL(a, b)` — string equality
- `LEN(str)` — string length
- `CONCAT(a, b, ...)` — string concatenation
- `SUBSTRING(str, start, len)` — substring extraction
- `DECIMAL_TO_STRING(num)` — number to string
- `REPLACEWITHASCII(str, search, ascii_code)` — character replacement
- `DATE(timestamp)` — timestamp to date string
- `DEC(value, divisor)` — integer division / floor
- `DEBUG(value)` — debug output (side effect)
- `SYSTEMINFO(field)` — system information
- `RANDOMSTRING(len)` — random string generation
- `SAVE_JSON(...)` — persist values (side effect)

### Trigger Mechanism
- `ALIAS.F := 1` — triggers execution of a `*WRITE` command
- `ALIAS.F := 0` — resets trigger after execution

**Total unique operators/functions: ~25+** (exceeds PRD's "likely required" estimate of ~15).

**Decision:** Sprint 0 parses and validates all of these syntactically. Semantic execution deferred to Sprint 1.

---

## 5. Pilot DDF Scope

| DDF | Status |
|-----|--------|
| Microsoft Calendar (`0x0D00007700010100`) | Primary pilot |
| Daikin Stylish (`0x0D00000D00010100`) | Secondary pilot |
| Microsoft Shifts (`0x0D00007700020100`) | Ignored for Sprint 0; bonus if time permits |

---

## 6. Updated Definition of Done

Changes to PRD Section 10:

| # | Original | Updated |
|---|----------|---------|
| 4 | Both pilots simulate against HAR captures, matching golden outputs | Both pilots **parse and lint clean** (zero errors). Simulation deferred to Sprint 1 |
| 8 | Formula engine implements audited operator set | Formula engine **parses and validates** audited operator set; execution stubbed |
| 9 | Six synthetic HAR fixtures exist | Deferred to Sprint 1 |
| 12 | Walkthrough runs end-to-end (parse, lint, simulate, sign) | Walkthrough covers **parse, lint, sign/verify** (no simulate) |

All other DoD items remain unchanged.

---

## 7. Sprint 1 Issues Created

- **GitHub Issue: "Implement DDF script-language interpreter"** — covers full execution engine for the operator set documented in Section 4 above
- **GitHub Issue: "Implement HAR-based simulator"** — covers simulator, golden harness, and synthetic HAR fixture creation; must account for `*READ`-empty / `*WRITE`-trigger pattern

---

*This document supplements the Sprint 0 PRD. In case of conflict, this document takes precedence.*
