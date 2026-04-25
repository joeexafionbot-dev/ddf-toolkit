# Sprint 0 PRD — DDF Toolkit Core

**Repo:** `mygekko/ddf-toolkit`
**Sprint duration:** 3 weeks
**Owner:** Joe (Claude Code) — implementation
**Reviewer:** Martin — manual PR review
**Status:** Ready to start
**Document version:** 1.0 — 25. April 2026

---

## 1. Mission

Build the foundational Python toolkit for working with myGEKKO DDF (Device Definition File) artifacts: parse, validate, lint, evaluate formulas, simulate REST traffic, sign with a test key. CLI-only. No UI.

This sprint creates the **substrate** every later sprint depends on:
- Sprint 1 will add a HAR-based capture recorder against real hardware on top of the Sprint 0 simulator.
- Sprint 2 will add an HA-Bridge DDF generator that uses the Sprint 0 linter and simulator as its quality gate.
- Phase-1 work (Composer Web-UI, Marketplace) layers UI/services over the same Sprint 0 core.

If Sprint 0 is solid, everything that follows is cheap. If Sprint 0 is rushed, every later sprint pays interest.

---

## 2. Out of scope (do not build)

These items are explicitly **not** Sprint 0. Surface them as future work in `ROADMAP.md`, but do not implement:

- Web UI / Composer (planned Sprint 3+)
- HA-Bridge DDF generator (planned Sprint 2)
- Hardware-based capture recorder (planned Sprint 1)
- Marketplace integration / submission workflow (Phase 1)
- Production signing-key integration — Sprint 0 uses a self-generated test key only
- BACnet / OPC-UA protocol support (Phase 2)
- Live integration against running myGEKKO controller

---

## 3. Decisions already made

Do not relitigate these. They are settled.

| # | Decision |
|---|---|
| 1 | Python **3.12** as minimum |
| 2 | Distribution: **pip package primary**, Docker image for CI |
| 3 | License: **Apache 2.0** |
| 4 | Review model Sprint 0: PRs from Joe → Martin reviews and merges |
| 5 | Signing in Sprint 0: **test key only**, generated locally; production-key code path stubbed |
| 6 | CI: **GitHub Actions** |
| 7 | Capture format: **HAR** (HTTP Archive 1.2 spec) |
| 8 | Formula engine: implement **only the operators used by Microsoft Calendar and Daikin Stylish DDFs**. Unsupported operators raise a clear `UnsupportedFormulaError`. Surface a tracked list in `docs/formula-coverage.md`. |
| 9 | Pilot DDFs: **Microsoft Calendar Gateway** (`0x0D00007700010100`) primary, **Daikin Stylish AC** (`0x0D00000D00010100`) secondary |

---

## 4. Repository layout

```
ddf-toolkit/
├── pyproject.toml              # PEP 621 metadata, build config
├── README.md
├── LICENSE                     # Apache 2.0
├── CONTRIBUTING.md
├── ROADMAP.md                  # public future-work list
├── CHANGELOG.md                # keepachangelog.com format
├── .github/
│   ├── workflows/
│   │   ├── ci.yml              # lint + test + build on push/PR
│   │   └── release.yml         # tag → PyPI + Docker Hub
│   ├── ISSUE_TEMPLATE/
│   └── PULL_REQUEST_TEMPLATE.md
├── .pre-commit-config.yaml     # ruff, mypy, end-of-file fixer
├── Dockerfile                  # python:3.12-slim base
├── docs/
│   ├── architecture.md
│   ├── formula-coverage.md     # operator support matrix
│   ├── ddf-schema.md           # canonical schema reference (extracted from DeviceLib.pdf)
│   └── cli-reference.md
├── src/ddf_toolkit/
│   ├── __init__.py
│   ├── cli.py                  # entry point: `ddf` command
│   ├── parser/                 # DDF CSV → AST
│   │   ├── __init__.py
│   │   ├── lexer.py
│   │   ├── parser.py
│   │   └── ast.py              # typed dataclasses for *GENERAL, *ITEM, *READ, *WRITE, *FORMULA, *ARGS, *LISTENER, *CONFIG, *GROUP, *OBJECT, *IO, *COMMAND
│   ├── linter/
│   │   ├── __init__.py
│   │   ├── rules.py            # rule registry; one rule = one class
│   │   └── reporter.py         # human-readable + JSON output
│   ├── formula/
│   │   ├── __init__.py
│   │   ├── lexer.py
│   │   ├── parser.py
│   │   ├── evaluator.py        # sandboxed; no eval(), no exec()
│   │   └── operators/          # one file per operator family
│   ├── signing/
│   │   ├── __init__.py
│   │   ├── keys.py             # test-key generation + load
│   │   ├── sign.py             # ECDSA-SHA384 over canonical DDF bytes
│   │   └── verify.py
│   ├── simulator/
│   │   ├── __init__.py
│   │   ├── har_loader.py       # HAR 1.2 parser
│   │   ├── mock_server.py      # aiohttp-based, plays HAR back
│   │   └── runner.py           # executes DDF READ/WRITE against mock; collects ITEM values
│   └── golden/
│       ├── __init__.py
│       └── runner.py           # golden-file comparison harness
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
│       ├── ddfs/               # sample DDFs
│       │   ├── microsoft_calendar.csv
│       │   └── daikin_stylish.csv
│       ├── captures/           # synthetic HAR files
│       │   ├── microsoft_calendar_oauth_flow.har
│       │   ├── microsoft_calendar_event_list.har
│       │   ├── microsoft_calendar_listener_webhook.har
│       │   └── daikin_stylish_status_poll.har
│       └── golden/             # expected ITEM-value outputs per (DDF, capture) pair
│           ├── microsoft_calendar_event_list.json
│           └── daikin_stylish_status_poll.json
└── examples/
    ├── README.md
    └── walkthrough.md          # narrative: parse → lint → simulate → sign
```

**Notes on the layout:**

- `src/` layout (not flat) is required — avoids accidental import of unbuilt code.
- One operator per file in `formula/operators/` keeps blast radius small when extending in Sprint 1+.
- `tests/fixtures/` is the single source of truth for example DDFs; do not duplicate them inside docs.
- `docs/ddf-schema.md` is **canonical** — extract it carefully from `DeviceLib.pdf` and treat it as the spec.

---

## 5. CLI surface

The Sprint 0 CLI must support the following commands. Use [Typer](https://typer.tiangolo.com/) or Click — Joe's choice; whichever has better type-hint integration in 3.12.

```bash
# Parsing & inspection
ddf parse <file.csv>                    # parse → pretty-print AST as YAML
ddf parse <file.csv> --json             # AST as JSON

# Validation & linting
ddf validate <file.csv>                 # schema validation only (pass/fail + reasons)
ddf lint <file.csv>                     # validate + style/best-practice rules
ddf lint <file.csv> --format json       # machine-readable for CI

# Formula evaluation
ddf formula eval "<expression>" --context <data.json>
                                        # one-shot evaluator for debugging

# Simulation
ddf simulate <file.csv> --capture <recording.har>
                                        # run DDF against captured traffic; print resulting ITEMs
ddf simulate <file.csv> --capture <recording.har> --golden <expected.json>
                                        # compare against golden file; non-zero exit on mismatch

# Signing
ddf sign <file.csv> --key <test-key.pem> -o <signed.csv>
ddf sign --test <file.csv> -o <signed.csv>
                                        # convenience: use bundled dev test key
ddf verify <signed.csv> --key <test-key.pub>

# Utility
ddf keygen --test -o <test-key.pem>     # generate ECDSA P-384 keypair for development
ddf version                              # version + git SHA
```

**Cross-cutting CLI requirements:**

- All commands must support `--quiet` and `--verbose`.
- Exit codes: `0` = success, `1` = validation/lint/simulate failure, `2` = usage error, `3` = internal error.
- Color output via `rich`, auto-disabled when not a TTY or when `NO_COLOR` env set.
- All commands must produce machine-readable JSON when `--format json` is passed (or `--json` for shorter form).
- The `ddf` entry point is registered via `[project.scripts]` in `pyproject.toml`.

---

## 6. Module specifications

### 6.1 Parser (`ddf_toolkit.parser`)

**Input:** DDF file as CSV (UTF-8 or CP1252 — auto-detect via BOM and `chardet` fallback).

**Output:** Typed AST as dataclasses. Every section gets its own dataclass. Examples:

```python
@dataclass(frozen=True)
class GeneralSection:
    device: str
    manufacturer: str
    protocol: Literal["REST", "MODBUS_TCP", "MODBUS_RTU", "MODBUS_ASCII", "SERCOM", "DMX512"]
    model_nr: str
    version_nr: str
    min_control_version: str
    timestamp: datetime
    debug_port: int | None
    listener_port: int | None
    connection: ConnectionConfig
    authentication: AuthConfig

@dataclass(frozen=True)
class Item:
    name: str
    type: Literal["BOOL", "INT", "FLOAT", "STRING", "ENUM"]
    access: Literal["R", "W", "RW"]
    unit: str | None
    formula: str | None
    description: str | None

@dataclass(frozen=True)
class DDF:
    general: GeneralSection
    config: list[ConfigField]
    args: list[ArgsDef]
    items: list[Item]
    reads: list[ReadCommand]
    writes: list[WriteCommand]
    listeners: list[ListenerDef]
    formulas: list[FormulaDef]
    groups: list[Group]
    objects: list[ObjectDef]
    ios: list[IODef]
    commands: list[Command]
    raw_source: str  # preserved for round-trip
```

**Acceptance criteria:**

- Parses both pilot DDFs without error.
- Preserves `raw_source` so signing operates on canonical bytes.
- Detects malformed sections and raises `DDFSyntaxError` with line number.
- 100% unit-test coverage on the parser package.

### 6.2 Linter (`ddf_toolkit.linter`)

Rule-based, each rule is a class with `code`, `severity` (`error` | `warning` | `info`), `check(ddf) -> list[Finding]`.

**Required Sprint 0 rules:**

- `DDF001` — `*WRITE` references undefined `ARG.X`
- `DDF002` — `*FORMULA` references undefined `DATA.x.y`
- `DDF003` — `*ITEM` declared but never read or written
- `DDF004` — `*LISTENER` port outside 8500–8600
- `DDF005` — `DEBUGPORT` outside 8500–8600
- `DDF006` — `MIN_CONTROL_VERSION` not parseable as semver
- `DDF007` — duplicate `*ITEM` name
- `DDF008` — duplicate `*ARGS` name
- `DDF009` — `AUTHENTICATION = PASSWORD` without `*CONFIG` field for credentials
- `DDF010` — `*ITEM` with formula references unknown source

**Acceptance criteria:**

- Both pilot DDFs lint clean (no errors). Warnings allowed and documented.
- `--format json` output validates against a published JSON Schema in `docs/`.
- Each rule has its own unit test with passing and failing fixture.

### 6.3 Formula engine (`ddf_toolkit.formula`)

**Lean scope (decision #8):** implement only the operators that actually appear in Microsoft Calendar and Daikin Stylish DDFs. Build a small auditing pass first that **scans both pilot DDFs and emits the list of operators encountered**, then implement that set.

Likely required operators based on prior inspection (verify by scanning):

- Path access: `DATA.VALUE.x.y`, `DATA.VALUE[i]`
- Search: `DATA.FIND(<path>, <key>, <value>)`
- HTTP introspection: `DATA.HTTP_CODE`
- Aggregation: `ARRAY.MAX`, `ARRAY.MIN`, `ARRAY.MEDIA` (note: `MEDIA` is "average" in DDF — German "Mittelwert", not "median"; document this trap)
- Arithmetic: `+`, `-`, `*`, `/`, parentheses
- Comparison: `==`, `!=`, `<`, `>`, `<=`, `>=`
- Logical: `AND`, `OR`, `NOT`
- Conditional: `IF(cond, then, else)`
- String: `CONCAT`, `SUBSTR` (only if used)
- Reverse formula (`RFORMULA`): inverse mapping for write-back

**Sandboxing requirements:**

- No `eval()`, no `exec()`, no `compile()`, no dynamic import.
- Pure tree-walking interpreter over the formula AST.
- Evaluator must time out after 100 ms per call (use `signal` or thread).
- Memory cap via input-size validation (formula source ≤ 4 KB).

**Acceptance criteria:**

- All operators in the audited set work end-to-end.
- Unsupported operators raise `UnsupportedFormulaError` listing the operator name and pointing to `docs/formula-coverage.md`.
- `docs/formula-coverage.md` lists every operator with status (✅ supported / ⏳ planned / ❌ not yet planned).

### 6.4 Simulator (`ddf_toolkit.simulator`)

**Capture format:** HAR 1.2 (industry standard, exportable from Chrome DevTools, Charles, mitmproxy, etc.).

**Approach:**

1. `har_loader.py` parses HAR, builds an in-memory request→response lookup keyed on `(method, url-pattern, body-hash)`.
2. `mock_server.py` is an `aiohttp` server that serves HAR responses; supports URL-pattern matching with parameter substitution (since DDF `*ARGS` produces dynamic URLs).
3. `runner.py` loads a DDF, points its `DOMAIN` at the mock server, executes all `*READ` commands, applies `*FORMULA` transforms, returns a dict of `{item_name: value}`.

**Constraint:** the mock server must support `*LISTENER` semantics by allowing a HAR entry tagged as a server-initiated event to be replayed into the DDF's listener port.

**Acceptance criteria:**

- Simulator runs the Microsoft Calendar DDF against `microsoft_calendar_event_list.har` and produces the expected ITEM values from `microsoft_calendar_event_list.json`.
- Simulator runs the Daikin Stylish DDF equivalent.
- Reasonable error messages when HAR has no matching response (e.g. "Request `GET /v1.0/me/events` not in capture").

### 6.5 Golden harness (`ddf_toolkit.golden`)

Thin layer over the simulator. Reads a pair `(ddf, capture, expected.json)`, runs simulation, diffs against `expected.json`, returns a pass/fail report with field-level differences.

**Acceptance criteria:**

- `pytest tests/integration/test_golden.py` runs all fixtures and passes.
- Adding a new golden fixture requires zero glue code — discovery is filesystem-based.

### 6.6 Signing (`ddf_toolkit.signing`)

ECDSA over P-384 (matches DeviceLib.pdf signature scheme: ECDSA-SHA384). Use [`cryptography`](https://cryptography.io/) — never roll your own.

**Sprint 0 signing model:**

- `ddf keygen --test` generates a P-384 keypair, saves to `~/.config/ddf-toolkit/test-key.{pem,pub}`.
- `ddf sign --test <file>` signs with that key, embeds signature as a `*SIGNATURE` section at end of CSV (or whatever the DeviceLib spec defines — confirm with Martin if ambiguous).
- `ddf verify <signed-file>` validates against the test-key public key by default; supports `--key <other.pub>` to verify production signatures **read-only** (we never sign with production keys in Sprint 0).

**Acceptance criteria:**

- Round-trip: parse → sign → verify passes for both pilots.
- Modified DDF (one byte changed in body) fails verification with clear error.
- Production-key code path is **stubbed** (raises `NotImplementedError("Production signing requires Sprint 5+")`) — the API exists, the implementation does not.

---

## 7. Synthetic capture fixtures

Since no hardware is available, the team will create synthetic HAR captures for both pilot DDFs. This is part of Sprint 0 deliverables.

**Microsoft Calendar HAR captures to produce:**

1. `microsoft_calendar_oauth_flow.har` — OAuth 2.0 device-code flow: device-code request → token poll → token success.
2. `microsoft_calendar_event_list.har` — `GET /v1.0/me/events` returning ≥3 calendar events with realistic shapes (UTC datetimes, attendees, `isAllDay`, recurrence).
3. `microsoft_calendar_listener_webhook.har` — incoming webhook for an `Event Created` notification (Microsoft Graph change notification format).

**Daikin Stylish HAR captures to produce:**

1. `daikin_stylish_status_poll.har` — polling current state (mode, setpoint, fan speed, indoor temp).
2. `daikin_stylish_set_mode.har` — write-side: setting cooling mode and target temperature.
3. `daikin_stylish_error_response.har` — Daikin returns a 503 / malformed response; tests robust handling.

**Quality bar for synthetic captures:**

- JSON shapes must match real vendor APIs as documented (Microsoft Graph reference, Daikin published API docs).
- Edge cases must be represented: empty arrays, null fields, error responses, timeouts.
- Each HAR includes a `comment` field on every entry explaining what scenario it represents.

These fixtures become the regression corpus — they outlive Sprint 0 and are used by every later sprint.

---

## 8. CI / quality gates

`.github/workflows/ci.yml`:

- Run on every push and PR.
- Matrix: Python 3.12 only (Sprint 0 — extend later if needed).
- Steps:
  1. Checkout
  2. `pip install -e ".[dev]"`
  3. `pre-commit run --all-files` (ruff format, ruff check, mypy strict)
  4. `pytest --cov=ddf_toolkit --cov-fail-under=85 tests/`
  5. `ddf validate tests/fixtures/ddfs/*.csv` — smoke test
  6. `ddf simulate tests/fixtures/ddfs/microsoft_calendar.csv --capture tests/fixtures/captures/microsoft_calendar_event_list.har --golden tests/fixtures/golden/microsoft_calendar_event_list.json`
  7. Build wheel + sdist with `python -m build`
  8. Build Docker image (no push in Sprint 0)

**`.pre-commit-config.yaml`:**

- `ruff` (format + lint)
- `mypy --strict` over `src/`
- `end-of-file-fixer`, `trailing-whitespace`, `check-yaml`, `check-toml`

**Coverage target Sprint 0:** 85% line coverage. Aspirational 90% for parser and linter (they have well-defined inputs/outputs).

---

## 9. Documentation deliverables

End of Sprint 0, the following docs must exist and be accurate:

- `README.md` — what is DDF, what is ddf-toolkit, install, 3 quick examples.
- `docs/architecture.md` — module map, data flow diagram (DDF → AST → linter/simulator/signer), extension points.
- `docs/ddf-schema.md` — canonical reference for DDF sections and their fields. Source: `DeviceLib.pdf`. Mark anything ambiguous with `// AMBIGUOUS — confirm with Martin`.
- `docs/formula-coverage.md` — operator support matrix.
- `docs/cli-reference.md` — every CLI command with examples.
- `CONTRIBUTING.md` — dev setup, PR conventions, commit-message style (Conventional Commits).
- `ROADMAP.md` — Sprints 1–8 outline (high level, no commitments beyond Sprint 1).

---

## 10. Definition of Done — Sprint 0

The sprint is **done** when all of the following are true. No partial credit.

1. ✅ Repo `mygekko/ddf-toolkit` exists on GitHub, public, Apache 2.0 licensed, with all files from §4 in place.
2. ✅ `pip install ddf-toolkit` works from a freshly built wheel; `ddf --help` shows all commands from §5.
3. ✅ `docker run mygekko/ddf-toolkit ddf --help` works from a locally built image.
4. ✅ Both pilot DDFs (`microsoft_calendar.csv`, `daikin_stylish.csv`) parse, lint clean (zero errors), and simulate against their HAR captures, matching their golden outputs.
5. ✅ `ddf sign --test` round-trips both pilots without error; `ddf verify` correctly accepts unmodified and rejects tampered files.
6. ✅ All required CLI commands from §5 exist and behave as specified.
7. ✅ All required linter rules (`DDF001`–`DDF010`) exist with passing/failing fixtures.
8. ✅ Formula engine implements the audited operator set; unsupported operators raise the documented error.
9. ✅ Six synthetic HAR fixtures exist in `tests/fixtures/captures/`.
10. ✅ CI passes: pre-commit clean, pytest ≥85% coverage, smoke tests green.
11. ✅ All docs from §9 exist and are reviewed by Martin.
12. ✅ Walkthrough in `examples/walkthrough.md` runs end-to-end on a fresh checkout.

---

## 11. Risks & open questions

Surface anything ambiguous early as a GitHub issue tagged `question`. Do not silently invent behaviour. Three known risks:

- **DeviceLib.pdf ambiguities.** Some DDF semantics may not be fully specified (e.g., exact format of `*SIGNATURE` section, behaviour when `*FORMULA` references a missing path). Where ambiguous, document the chosen interpretation in `docs/ddf-schema.md` and flag for Martin's review.
- **Synthetic HAR realism.** If our synthetic captures diverge significantly from real Microsoft Graph or Daikin responses, Sprint 1 (real capture recording) will surface bugs the simulator hides. Mitigation: cross-reference against published API docs as exhaustively as possible.
- **Operator audit drift.** The lean formula scope assumes the auditor pass finds a manageable operator set. If the pilot DDFs use 30+ operators, scope decision #8 should be reopened with Martin before implementing.

---

## 12. First three days — concrete starting steps

To remove ambiguity on "where do I begin":

**Day 1**
- Create the repo, scaffold from §4, get CI green on a hello-world test.
- Write `pyproject.toml`, `Dockerfile`, `.pre-commit-config.yaml`, basic `README.md`.
- Open a draft PR with the scaffolding for Martin to review tooling choices early.

**Day 2**
- Read `DeviceLib.pdf` end-to-end. Draft `docs/ddf-schema.md` from it.
- Copy both pilot DDFs into `tests/fixtures/ddfs/`.
- Stand up the parser skeleton with one passing test for `*GENERAL`.

**Day 3**
- Run the formula-operator audit pass over both pilot DDFs.
- Open a GitHub issue listing the operator set found — wait for Martin's ack before implementing.
- Start the linter skeleton with `DDF001` as the first concrete rule.

After Day 3 the path is mechanical: parser → linter → formula → simulator → signing → docs → polish.

---

*End of PRD. Questions to Martin via GitHub issues, not Slack.*
