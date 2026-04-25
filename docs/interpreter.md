# DDF Script Interpreter

The interpreter executes DDF formula scripts against a pluggable runtime environment.

## Architecture

```
Formula Source → Lexer → Tokens → Parser → AST → Interpreter → Environment
```

- **Lexer** (`formula/lexer.py`): Tokenizes formula strings
- **Parser** (`formula/parser.py`): Recursive-descent parser producing typed AST
- **AST** (`formula/ast.py`): Typed nodes (AssignStmt, IfStmt, BinaryOp, FunctionCall, etc.)
- **Interpreter** (`interpreter/evaluator.py`): Tree-walking evaluator
- **Environment** (`interpreter/environment.py`): Pluggable state and side-effect handlers

## State Spaces

| Namespace | Access Pattern | Scope |
|-----------|---------------|-------|
| `$.GPARAM.*` | Main device parameters | Persists across simulation |
| `$.PARAM.*` | Sub-device (slave) parameters | Per-WRITE, populated by ARGS |
| `$.SYS.TIME` | System time (epoch seconds) | Read-only, frozen in tests |
| `$.CONFIG.*` | User config fields (max 3) | Read-only in formulas |
| `X.{ID}` | Item variables by numeric ID | Persists across simulation |
| `TEMPVAR` | Named temporary variables | Device-scoped |
| `ALIAS.F` | Write trigger flag | Reset by formula |
| `ALIAS.HTTP_CODE` | HTTP response code | Set after HTTP request |
| `ALIAS.VALUE.*` | JSON response body path | Set after HTTP request |

> **$.PARAM vs $.GPARAM:** `$.GPARAM` is the main device and persists. `$.PARAM` is per-slave
> and populated by `*ARGS` for each `*WRITE` execution. In single-slave test mode, `params` starts
> empty. // AMBIGUOUS — production behavior may differ.

## Sandboxing

- No `eval()`, `exec()`, `compile()`, `__import__()`
- Per-script execution timeout: 5 seconds (configurable)
- Step limit: 100,000 statements per script
- String concatenation cap: 1 MB
- All filesystem access via `Environment.save_json()` only

## Side-Effect Operators

| Function | Test Mode | Production Mode |
|----------|-----------|-----------------|
| `DEBUG(var1, ...)` | Captured to `env.debug_log` | Output to debug TCP port |
| `SAVE_JSON(...)` | Captured to `env.saved_json` (in-memory map) | Write to JSON file (overwrite) |
| `RANDOMSTRING(len)` | Deterministic: "AAA..." | Cryptographic random |
| `SYSTEMINFO(key)` | Fixed test values | Real controller info |

> **SAVE_JSON semantics:** Overwrite, not append. Path relative to DDF file location.
> // AMBIGUOUS — exact production path resolution needs confirmation.

## Trigger-Flag Execution Model

DDF formulas don't execute linearly. The `*WRITE` sections use trigger flags:

1. `RFORMULA` runs periodically, checks conditions, sets `ALIAS.F := 1`
2. The runtime detects the flag and executes the `*WRITE` command
3. The `*WRITE` formula processes the HTTP response and resets the flag (`ALIAS.F := 0`)

This is a state machine, not procedural code. The simulator runner implements this model.
