# Sprint 1 PRD — DDF Script Interpreter + HAR Simulator

**Repo:** `joeexafionbot-dev/ddf-toolkit`
**Sprint duration:** TBD — Joe estimates after reading; Martin decides
**Owner:** Joe (Claude Code) — implementation
**Reviewer:** Martin — manual PR review (Claude Code GitHub Action as supplementary AI reviewer from this sprint onward)
**Predecessor:** Sprint 0 (v0.1.0 shipped — parser, linter, signing-verify, AST)
**Document version:** 1.0 — 25. April 2026

---

## 0. Why this PRD exists

Sprint 0 produced two artifacts that change how this PRD must be written:

1. **A working AST** that reflects the *actual* structure of pilot DDFs — not what the original DeviceLib-PDF reading suggested.
2. **A pre-implementation reality check** (`docs/internal/SPRINT_0_AMENDMENTS.md`) that revealed DDF formulas are an **imperative scripting language** with side effects, not pure expressions.

Sprint 1 builds on those findings directly. There is no longer any "PRD vs reality" gap. This PRD treats the Sprint-0 Amendments document as the authoritative spec for what the language *is*, and asks Sprint 1 to make it *executable*.

The work is genuinely harder than Sprint 0 — interpreters with side effects are categorically more complex than parsers — but the foundation is solid, so the path is clear.

---

## 1. Mission

Make every DDF in the wild **executable in a deterministic test environment**.

Sprint 0 answered "what does this DDF say?" Sprint 1 answers "what does this DDF *do*?" — without controller hardware, without external network, without flaky timing.

Two deliverables, in dependency order:

- **DDF Script Interpreter** — tree-walking evaluator over the Sprint-0 AST that executes the imperative DDF scripting language (assignments, block-IF, side effects, ~25 operators) in a sandboxed, deterministic, mockable runtime.
- **HAR-based Simulator** — runner that wires the interpreter to recorded HTTP traffic (HAR files), replays request/response pairs, drives `*WRITE` trigger flags, and reports resulting `*ITEM` and `$.GPARAM` state.

When both are done, every Sprint-0 DDF can be exercised end-to-end against synthetic captures, and Sprint-2+ work (HA-Bridge generator, §14a profiles, marketplace submissions) gets free regression testing.

---

## 2. What this sprint is *not*

Out of scope. Open issues for these, do not implement:

- HA-Bridge DDF generator (Sprint 2)
- Real-hardware capture recorder (Sprint 2 or 3 — under review)
- Web UI / Composer (Phase 1, post-MVP)
- BACnet / OPC-UA protocol drivers (Phase 2)
- Production signing-key integration (separate hardening track)
- Marketplace integration (Phase 1)
- Performance optimisation beyond "doesn't time out on pilot DDFs"

---

## 3. Decisions already made

Settled. Do not relitigate.

| # | Decision |
|---|---|
| 1 | Sprint-1 path = **Interpreter + Simulator** (Pfad A) |
| 2 | Interpreter scope = **full DDF script language as observed in pilot DDFs** (all ~25 operators identified in Amendments §4) — no `NotImplementedError` shortcuts for operators that appear in the pilots |
| 3 | Repo stays **public OSS, Apache 2.0** |
| 4 | Pilot DDFs unchanged: **Microsoft Calendar primary, Daikin Stylish secondary** |
| 5 | Capture format: **HAR 1.2** (continued from Sprint 0) |
| 6 | Time control: **`freezegun`** or **`time-machine`** — Joe picks |
| 7 | Side-effect operators (`SAVE_JSON`, `DEBUG`, `RANDOMSTRING`, `SYSTEMINFO`): **mockable via dependency injection**; default test mode uses deterministic stubs |
| 8 | Interpreter is **tree-walking, single-threaded**; performance target is "completes pilot-DDF runs in <5s on dev laptop" — no JIT, no compilation tier |
| 9 | Sandboxing: **same constraints as Sprint 0 §6.3** — no `eval`, no `exec`, no `compile`, no dynamic import, no network unless via the simulator's mock layer |

---

## 4. Inputs from Sprint 0 — read these first

Before writing any Sprint-1 code, Joe must re-read:

- `docs/internal/SPRINT_0_AMENDMENTS.md` — especially §4 (operator audit) and §1.2/1.3 (the `*WRITE`-trigger pattern)
- `docs/architecture.md` — final AST shape
- `docs/ddf-schema.md` — DDF spec including AMBIGUOUS markers (Sprint 1 will resolve some of them)
- `src/ddf_toolkit/parser/ast.py` — typed dataclasses already in place
- The two pilot DDFs themselves — `tests/fixtures/ddfs/microsoft_calendar.csv`, `tests/fixtures/ddfs/daikin_stylish.csv`

The Amendments document is the **specification** for the DDF script language. Anything ambiguous there gets resolved during Sprint 1 and pushed back as PRs to that document.

---

## 5. Architecture overview

```
                     ┌──────────────────────────┐
                     │  ddf simulate <ddf>      │
                     │       --capture <har>    │
                     │       --golden <expected>│
                     └────────────┬─────────────┘
                                  │
                  ┌───────────────┴───────────────┐
                  │                               │
         ┌────────▼────────┐             ┌────────▼─────────┐
         │  HAR Loader     │             │  AST (Sprint 0)  │
         │  (request→resp) │             │  parser output   │
         └────────┬────────┘             └────────┬─────────┘
                  │                               │
                  │      ┌──────────────────┐     │
                  └─────►│  Mock Server     │◄────┘
                         │  (aiohttp)       │
                         └────────┬─────────┘
                                  │
                         ┌────────▼─────────┐
                         │  Simulator       │
                         │  Runner          │
                         │  (drives writes, │
                         │   trigger flags) │
                         └────────┬─────────┘
                                  │
                  ┌───────────────▼─────────────────┐
                  │  Interpreter (Sprint 1 core)    │
                  │  ┌────────────┐ ┌────────────┐  │
                  │  │ Evaluator  │ │ Environment│  │
                  │  │ tree-walk  │◄►│ $.GPARAM,  │  │
                  │  │            │ │ X.n, flags │  │
                  │  └─────┬──────┘ └────────────┘  │
                  │        │                        │
                  │  ┌─────▼─────────────────────┐  │
                  │  │ Operator Library          │  │
                  │  │ - arithmetic, comparison  │  │
                  │  │ - IF/ELSE/ENDIF (block)   │  │
                  │  │ - ISEQUAL, LEN, CONCAT    │  │
                  │  │ - DATE, DEC, SUBSTRING    │  │
                  │  │ - DEBUG, SAVE_JSON        │  │ ◄── pluggable side-effect mocks
                  │  │ - RANDOMSTRING, SYSTEMINFO│  │
                  │  │ - HTTP_CODE, HTTP_DATA    │  │
                  │  │ - .ASLIST, .ARRAY.LEN     │  │
                  │  │ - REPLACEWITHASCII        │  │
                  │  │ - DECIMAL_TO_STRING       │  │
                  │  └───────────────────────────┘  │
                  └─────────────────────────────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │  Result          │
                         │  - ITEM values   │
                         │  - GPARAM state  │
                         │  - logs/debug    │
                         └──────────────────┘
```

Key design separations:

- **Interpreter knows nothing about HTTP.** It calls into an `Environment` abstraction that exposes `do_http_request(method, url, headers, body) -> Response`. In production this hits the real network; in tests it hits the mock server. This is the most important architectural line — break it and you get untestable code.
- **Side-effect operators delegate.** `SAVE_JSON` calls `env.save_json(path, data)`. `DEBUG` calls `env.debug(msg)`. The default test environment captures these into a list for assertions; a production environment would actually do them.
- **Trigger flags are state, not control flow.** Setting `GETTOKEN.F := 1` does not directly call anything. The simulator runner observes `.F` flag transitions and decides which `*WRITE` block to fire next. This matches DDF semantics from the Amendments doc.

---

## 6. Module specifications

### 6.1 Interpreter (`ddf_toolkit.interpreter`)

**Purpose:** Walk the Sprint-0 AST for DDF script blocks and execute them.

**Key abstractions:**

```python
@dataclass
class Environment:
    """Pluggable runtime context. Default implementation is for tests."""
    gparams: dict[str, Any]
    sys_vars: dict[str, Any]            # $.SYS.TIME, $.SYS.UPTIME, ...
    config: dict[str, Any]              # $.CONFIG.* — from *CONFIG section
    params: dict[str, Any]              # $.PARAM.* — from *ARGS

    def http_request(self, ...) -> HttpResponse: ...
    def save_json(self, path: str, data: Any) -> None: ...
    def debug(self, msg: str) -> None: ...
    def random_string(self, length: int) -> str: ...
    def system_info(self, key: str) -> Any: ...
    def now(self) -> datetime: ...      # frozen in tests

class Interpreter:
    def __init__(self, env: Environment, ddf: DDF) -> None: ...
    def execute(self, script: ScriptBlock) -> None: ...
    def evaluate(self, expr: Expression) -> Any: ...
```

**Operator coverage (decision #2 — full):**

Joe's Sprint-0 audit identified the following operators in the pilot DDFs. Every one of them must work end-to-end in Sprint 1:

| Family | Operators |
|---|---|
| Arithmetic | `+`, `-`, `*`, `/` |
| Comparison | `==`, `!=`, `<`, `>`, `<=`, `>=`, `ISEQUAL()` |
| Logical | `&&`, `\|\|`, `!`, `AND`, `OR`, `NOT` |
| Control flow | `IF`/`THEN`/`ELSE IF`/`ELSE`/`ENDIF` (block-structured), `;` (statement separator), `:=` (assignment) |
| String | `CONCAT()`, `SUBSTRING()`, `LEN()`, `REPLACEWITHASCII()`, `DECIMAL_TO_STRING()` |
| Number | `DEC()` |
| Date/Time | `DATE()`, `$.SYS.TIME` |
| Collections | `.ASLIST`, `.ARRAY.LEN` |
| HTTP introspection | `HTTP_CODE`, `HTTP_DATA`, `.URL`, `.T`, `.F` (trigger/finish flags) |
| State access | `$.GPARAM.*`, `$.SYS.*`, `$.CONFIG.*`, `$.PARAM.*`, `X.n`, named aliases |
| Side effects | `DEBUG()`, `SAVE_JSON()`, `RANDOMSTRING()`, `SYSTEMINFO()` |

If an additional operator surfaces during implementation that's used by either pilot but missed in the Sprint-0 audit, treat it as in-scope and add to the list. If an operator surfaces that's *not* used by either pilot, file a Sprint-2 issue and `NotImplementedError` it for now.

**Sandboxing requirements:**

- No `eval()`, `exec()`, `compile()`, `__import__()`, or dynamic attribute access on system modules.
- Per-script execution timeout (default 5s; configurable per call).
- Memory cap on string concatenation (max 1 MB result) to prevent runaway loops.
- All filesystem access goes through `Environment.save_json()` — no direct `open()`.

**Acceptance criteria:**

- Both pilot DDFs execute through the interpreter without raising for any reason except an explicit `Environment` mock returning an error.
- Every operator has a unit test (passing fixture + edge case).
- Time-dependent code (`DATE()`, `$.SYS.TIME`) is fully deterministic under `freezegun`/`time-machine`.
- Side-effect operators capture their effects into `Environment` accumulators for test assertions.
- Interpreter coverage ≥90% — this is the riskiest module, treat coverage seriously.

### 6.2 HAR Loader (`ddf_toolkit.simulator.har_loader`)

**Purpose:** Load HAR 1.2 file, expose request→response lookups by URL pattern + method (+ optional body hash for POST disambiguation).

**Approach:**

- Parse HAR JSON, build indexed lookup keyed on `(method, url-pattern)`.
- URL patterns support placeholder substitution: a HAR entry recorded as `GET /v1.0/me/events?$top=10` matches a runtime request to `GET /v1.0/me/events?$top=20` only if the test author opts into pattern-relaxation; default is exact match.
- Provide a `match(request) -> response | None` API.
- Return `None` (and clear log line) when no match — never silently fall through.

**Acceptance criteria:**

- All six Sprint-1 HAR fixtures load without parser errors.
- Exact-match lookup works for all pilot scenarios.
- Pattern-relaxation can be enabled per-fixture (e.g., for date-stamped query parameters).
- Unit-tested against malformed HAR (invalid JSON, missing fields, wrong version) — fails clearly, doesn't crash.

### 6.3 Mock Server (`ddf_toolkit.simulator.mock_server`)

**Purpose:** aiohttp server that serves HAR-recorded responses to interpreter HTTP calls.

**Approach:**

- Lightweight aiohttp app, ephemeral port.
- On startup, accepts a `HARLoader` instance.
- For every incoming request, calls `loader.match()`, returns the response or 404.
- Supports `*LISTENER` semantics: a special HAR entry tagged `"_simulated_event": true` can be replayed *into* the DDF's listener port on a schedule (e.g., "5 seconds after simulator start, fire this webhook payload"). This is the trick to make event-driven DDFs testable.
- Logs every request/response pair with timing into a structured log file for debugging.

**Acceptance criteria:**

- Mock server starts in <500ms and accepts connections on a dynamic port.
- Microsoft Calendar OAuth flow runs end-to-end (device-code → token-poll → token-issued → first authenticated request).
- Listener-event injection works: webhook fires during simulation, DDF processes it.
- Server shuts down cleanly even if a test panics (use `pytest` fixture with `try/finally` teardown).

### 6.4 Simulator Runner (`ddf_toolkit.simulator.runner`)

**Purpose:** Orchestrate the full simulation. Load DDF, point its `DOMAIN` at the mock server, drive `*WRITE` trigger flags, collect resulting state.

**Trigger-flag execution model (critical, from Sprint-0 finding):**

```
1. Initialise interpreter with empty state.
2. Identify *WRITE blocks with their trigger conditions (e.g., GETTOKEN.F == 1).
3. Determine boot-time triggers: which writes auto-fire on simulation start?
   (Inspect the DDF for unconditional initial-state assignments.)
4. Loop:
   a. Find first *WRITE whose trigger condition evaluates true.
   b. Execute its FORMULA block via interpreter.
   c. Issue HTTP request (intercepted by mock server).
   d. Run response-handling FORMULA on the response.
   e. Update GPARAMs / X.n / ITEM values per response formulas.
   f. Continue until no triggered write remains, or step limit reached (default 100).
5. Capture final ITEM / GPARAM state. Return as Result object.
```

**Listener handling:** if HAR has `_simulated_event` entries, the runner schedules them to fire after the boot phase, then re-enters the loop until all events processed.

**Acceptance criteria:**

- Microsoft Calendar pilot: simulator runs OAuth+event-list flow, populates expected ITEM values matching the Sprint-1 golden fixture.
- Daikin Stylish pilot: simulator polls status, sets target temperature, processes error response, all matching golden fixtures.
- Step limit prevents infinite loops; runner exits with clear error message if hit.
- Result object includes: ITEM values, GPARAM final state, list of HTTP requests made, list of side-effect calls captured, total wall-clock time.

### 6.5 Golden Harness (`ddf_toolkit.golden`) — extension

The Sprint-0 golden runner already exists as a stub. Sprint 1 extends it:

- Compare not only ITEM values, but also GPARAM state, side-effect log, and (optionally) HTTP request sequence.
- Better diff output: show field-level differences with paths (e.g., `gparams.access_token: expected "abc...", got "xyz..."`).
- Support "ignore fields" patterns for non-deterministic data (e.g., timestamps not under freezegun control).

---

## 7. HAR fixture plan

Six synthetic captures, three per pilot. These are part of Sprint 1 deliverables, not Sprint 0.

### Microsoft Calendar (3 fixtures)

1. **`microsoft_calendar_oauth_flow.har`**
   - `POST https://login.microsoftonline.com/.../devicecode` → device code response
   - `POST https://login.microsoftonline.com/.../token` (poll, 1st) → `authorization_pending`
   - `POST https://login.microsoftonline.com/.../token` (poll, 2nd) → token issued
   - **Golden:** `gparams.access_token` populated, `gparams.refresh_token` populated, no errors

2. **`microsoft_calendar_event_list.har`**
   - Pre-condition: token present (test composes with fixture #1, or starts in post-OAuth state)
   - `GET https://graph.microsoft.com/v1.0/me/events?$top=10` → 3 events with realistic shapes
   - Event shapes: one all-day, one timed, one recurring; UTC datetimes; attendees array
   - **Golden:** specific ITEM values populated per the DDF's mapping logic

3. **`microsoft_calendar_listener_webhook.har`**
   - Simulated event: Microsoft Graph change notification arrives at DDF's `*LISTENER` port
   - Notification body matches Microsoft's published `clientState`/`subscriptionId` format
   - **Golden:** subscription validation handled, event payload triggers correct ITEM update

### Daikin Stylish (3 fixtures)

1. **`daikin_stylish_status_poll.har`**
   - Multi-endpoint status poll typical of the unofficial Daikin REST API surface (refer to `pydaikin` library on PyPI for endpoint shapes — Daikin has no official public docs)
   - Returns: indoor temperature, outdoor temperature, current mode, setpoint, fan speed, error code (none)
   - **Golden:** corresponding ITEMs populated, no error flag set

2. **`daikin_stylish_set_mode.har`**
   - Write-side: simulator drives a mode-change command (cooling, 22°C target)
   - HAR contains the expected POST/GET sequence
   - **Golden:** confirmation ITEM set, side-effect log shows the SET command

3. **`daikin_stylish_error_response.har`**
   - Status endpoint returns 503 once, then recovers on retry
   - Tests robust handling: error flag set during failure, cleared on recovery
   - **Golden:** error counter incremented, final state is healthy

**Quality bar (continued from Sprint 0):**

- JSON shapes match real vendor APIs as closely as possible.
- Edge cases represented: empty arrays, null fields, error responses.
- Each HAR entry carries a `comment` explaining the scenario.
- Reference docs cited in `docs/captures-research.md` (new file) — Microsoft Graph reference URLs, `pydaikin` source links.

---

## 8. CLI extensions

The Sprint-0 CLI gains new commands and arguments. No breaking changes to existing commands.

```bash
# Expanded simulate (Sprint 0 stub becomes real)
ddf simulate <ddf.csv> --capture <recording.har>
ddf simulate <ddf.csv> --capture <recording.har> --golden <expected.json>
ddf simulate <ddf.csv> --capture <recording.har> --step-limit 50
ddf simulate <ddf.csv> --capture <recording.har> --freeze-time "2026-04-25T10:00:00Z"
ddf simulate <ddf.csv> --capture <recording.har> --gparam KEY=VALUE  # initial state
ddf simulate <ddf.csv> --capture <recording.har> --log-http requests.log

# New: standalone interpreter for debugging
ddf eval-script <ddf.csv> --section WRITE --name <write_name> --context <ctx.json>

# New: HAR utilities
ddf har validate <recording.har>
ddf har list <recording.har>           # show indexed entries
```

---

## 9. CI / quality gates

Extends the Sprint-0 GitHub Actions workflow. Additions:

- New job `simulate-pilots` that runs both pilot DDFs against their golden fixtures on every PR.
- Coverage target raised: **88%** overall, **90%** on `interpreter/` package.
- New nightly job (cron, weekly is fine for Sprint 1) that exercises the simulator with random HAR-replay-order to catch ordering bugs.
- Pre-existing Sprint-0 jobs (lint, test, build, Docker) unchanged.

**Claude Code GitHub Action (decision from earlier):** enabled from Sprint 1 onwards as supplementary AI reviewer on PRs. Configuration goes into `.github/workflows/claude-review.yml`. Reviewer prompt to be drafted by Joe in Day 1 (not a separate task).

---

## 10. Documentation deliverables

End of Sprint 1, in addition to keeping Sprint-0 docs current:

- `docs/interpreter.md` — language reference: every operator, every state space (`$.GPARAM`, `$.SYS`, `X.n`, etc.), evaluation semantics, side-effect taxonomy.
- `docs/simulator.md` — how the simulator works, trigger-flag execution model, HAR fixture authoring guide, golden-file format.
- `docs/captures-research.md` — references to vendor API docs used to author synthetic HARs.
- `docs/internal/SPRINT_1_AMENDMENTS.md` — same pattern as Sprint 0: any reality-vs-PRD gaps surfaced during implementation get captured here.
- Updated `docs/cli-reference.md` covering new commands.
- Updated `docs/formula-coverage.md` — every operator now ✅, no ⏳.
- `CHANGELOG.md` entry for v0.2.0.

---

## 11. Definition of Done — Sprint 1

The sprint is **done** when *all* of the following are true:

1. ✅ Interpreter executes both pilot DDFs end-to-end without errors.
2. ✅ Every operator from Amendments §4 has an implementation and unit test (pass + edge case).
3. ✅ Six HAR fixtures exist in `tests/fixtures/captures/` with associated goldens.
4. ✅ `ddf simulate <pilot> --capture <har> --golden <expected>` returns exit 0 for all six fixture pairs.
5. ✅ Time-dependent operators are deterministic under freezegun/time-machine — the same simulation run twice produces byte-identical output.
6. ✅ Side-effect operators (`SAVE_JSON`, `DEBUG`, etc.) are mockable via the `Environment` abstraction; defaults capture into accumulators.
7. ✅ Mock server starts/stops cleanly in tests; no port leakage; works in parallel pytest workers.
8. ✅ CI green: lint, types, tests ≥88% overall and ≥90% on interpreter, smoke tests pass.
9. ✅ Claude Code GitHub Action installed and producing review comments on PRs.
10. ✅ All docs from §10 exist, accurate, reviewed by Martin.
11. ✅ `CHANGELOG.md` and `pyproject.toml` reflect v0.2.0; tag pushed.
12. ✅ The two Sprint-1 issues (#1 interpreter, #2 simulator) closed referencing the merge commit.

---

## 12. Risks & open questions

Surface as GitHub issues tagged `question` early. Known risks:

- **Side-effect operator semantics may be ambiguous.** `SAVE_JSON` — does it save relative to controller working dir? Append or overwrite? `DEBUG` — TCP socket lifetime per-script or per-DDF? Some of these aren't pinned by DeviceLib.pdf. When ambiguous: pick a reasonable behaviour, document in `docs/interpreter.md`, mark as AMBIGUOUS, move on.
- **Trigger-flag scheduling order.** If two `*WRITE` blocks become triggerable in the same step, which fires first? DDF spec may not specify. Default: deterministic order (lexical position in DDF). Document.
- **Daikin API realism.** No official Daikin docs; `pydaikin` is community-maintained reverse-engineering. Synthetic HARs may diverge from real device behaviour. Sprint 2's hardware-recorder will surface this — for now, accept the gap and document.
- **Performance on larger DDFs.** Sprint-1 target is "pilots run in <5s". When third-party DDFs come (Sprint 2/3), some may be 5–10× larger. Premature optimisation is wrong here, but Joe should keep the interpreter implementation amenable to later profiling (no early caching that complicates the code).
- **Listener fixture authoring.** Simulating server-pushed events into a TCP listener is the trickiest part of the simulator. If Joe finds the design in §6.3 unworkable mid-sprint, escalate immediately rather than work around silently.

---

## 13. Joe — first reading + estimation request

Before any code:

1. Re-read the Sprint-0 Amendments document end-to-end. The operator audit there is your spec.
2. Spend up to half a day building a one-page mental model of the interpreter architecture — confirm or push back on §5.
3. Produce an estimate covering:
   - Total sprint length (in working days, not calendar weeks)
   - Breakdown by major module (interpreter core, operators by family, mock server, runner, fixtures, docs)
   - Three highest risks, with proposed mitigation
   - Anything in this PRD that is wrong, ambiguous, or contradicts Sprint-0 reality

Same rule as Sprint 0: read, think, answer. No code yet. PRD ambiguity gets clarified before Day 1, not during it.

---

*End of PRD. Questions to Martin via GitHub issues, not Slack.*
