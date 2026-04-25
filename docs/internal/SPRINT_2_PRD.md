# Sprint 2 PRD — HA-Bridge DDF Generator

> **Amendment notice (2026-04-25):** Pre-implementation review found two bugs (missing AST→CSV serializer, incorrect `build_formulas` contract) and 8 scope decisions. See [SPRINT_2_AMENDMENTS.md](SPRINT_2_AMENDMENTS.md) for binding changes. In case of conflict, the amendments document takes precedence.

**Repo:** `joeexafionbot-dev/ddf-toolkit`
**Sprint duration:** 3 weeks (15 working days), with optional Stretch Week 4 — Joe-gated
**Owner:** Joe (Claude Code) — implementation
**Reviewer:** Martin — manual PR review + Claude Code GitHub Action (supplementary AI review)
**Predecessors:** Sprint 0 (v0.1.0 — parser, linter, signing-verify), Sprint 1 (v0.2.0 — interpreter, simulator)
**Document version:** 1.0 — 25. April 2026

---

## 0. Why this sprint exists

Sprints 0 and 1 produced a toolkit that can read, validate, lint, execute, and simulate *existing* DDFs. That's powerful internally, but every DDF in the system was hand-written. The toolkit's economic value scales only when it can *generate* DDFs — at which point a single Joe-week produces what previously took an integrator-quarter.

Home Assistant is the highest-leverage entry point for generation:

- **Uniform abstraction over chaos.** HA wraps ~3000 vendor integrations behind one REST API. We don't have to learn Hue, Sonoff, Aqara, or Daikin protocols — HA already did. We map *HA's normalized model* to DDF, once.
- **Massive multiplier.** Every HA integration that wasn't reachable via DDF before is reachable through the bridge.
- **Strategic alignment with SmartBridge.** This sprint is the technical foundation of the "HA as invisible infrastructure" thesis. SmartBridge will sit on top of it.

Sprint 2's first principle: **what we generate must round-trip cleanly through the linter (Sprint 0) and simulator (Sprint 1).** A generator without round-trip validation produces fluff. With it, every output is provably executable before it touches a controller.

---

## 1. Mission

Generate signed, simulator-validated DDFs from a Home Assistant instance, covering the ten most common entity domains, with a hard guarantee that every generated DDF executes cleanly against captured HA traffic.

Three deliverables, in dependency order:

1. **HA Source Adapter** — load entity catalog from a live HA instance (REST API + long-lived token) or from a snapshot JSON file. Snapshot is the deterministic CI mode; live is the realism anchor.
2. **Mapping Engine** — domain-specific templates that translate HA entities into DDF structures (`*ITEM`, `*WRITE`, `*FORMULA`). Ten domains in scope, each with its own template module.
3. **Round-Trip Validation Pipeline** — generated DDF → linter → simulator → golden assertion. No DDF leaves the generator without passing the pipeline.

Stretch (Joe-gated, see §11): real-hardware integration test against one HA-controlled device.

---

## 2. What this sprint is *not*

Out of scope. File issues for these, do not implement:

- DDF Composer Web-UI (Phase 1)
- Marketplace integration / submission workflow (Phase 1)
- §14a / EEBUS / SMGW compliance profiles (separate Compliance-Suite track)
- BACnet / OPC-UA protocol drivers (Phase 2)
- Real-hardware capture recorder against Modbus/Serial devices (Sprint 3+)
- Production signing-key integration (separate hardening track)
- HA domains beyond the Top-10 (Sprint 3 candidates: alarm_control_panel, water_heater, humidifier, siren, valve, update, weather, calendar, button, scene, automation, script)
- HA add-on or plug-in form-factor (we generate DDFs, we don't run inside HA)
- HA-API write-path optimisation beyond what the Top-10 domains require

---

## 3. Decisions already made

Settled. Do not relitigate.

| # | Decision |
|---|---|
| 1 | Sprint-2 scope = HA-Bridge DDF Generator with Round-Trip Validation |
| 2 | Top-10 domains in scope: `light`, `switch`, `sensor`, `binary_sensor`, `climate`, `cover`, `media_player`, `lock`, `fan`, `vacuum` |
| 3 | HA test source: HA running in Docker on the Hostinger VPS (Martin provides URL + long-lived token in Day 1) |
| 4 | Generator accepts both **live HA REST API** and **snapshot JSON file** as input. Snapshot is the default for CI; live is for realism testing. |
| 5 | DDF granularity: **one DDF per HA integration family**, not per entity. All `light.*` from Hue → one DDF. All `light.*` from a different brand → another DDF. Discriminator is the entity's `device.manufacturer` field. |
| 6 | Round-Trip pipeline is **mandatory before commit**. CI rejects any generated DDF that doesn't pass linter + simulator. |
| 7 | Real-hardware integration is **Stretch (Week 4), Joe-gated**: only if Generator + Round-Trip is fully green by end of Week 2. Hardware choice deferred to Joe based on availability. |
| 8 | Repo stays **public OSS, Apache 2.0** |

---

## 4. Inputs from prior sprints — read these first

Joe must re-read before any code:

- `docs/internal/SPRINT_0_AMENDMENTS.md` — DDF script-language reality
- `docs/internal/SPRINT_1_AMENDMENTS.md` — interpreter/simulator design notes
- `docs/architecture.md` — final AST, parser API, signing API
- `docs/interpreter.md` — operator semantics, environment model
- `docs/simulator.md` — runner state machine, trigger flag execution
- `tests/fixtures/ddfs/microsoft_calendar.csv` and `daikin_stylish.csv` — they are the **template** for what good DDFs look like

The pilot DDFs are the gold standard. Generated DDFs should pattern-match them in shape, idiom, and `*FORMULA` conventions — not invent new styles.

---

## 5. Architecture

```
┌─────────────────────────────┐         ┌──────────────────────────┐
│  Live HA Instance           │         │  HA Snapshot JSON file   │
│  (Hostinger Docker)         │         │  (tests/fixtures)        │
│  - GET /api/states          │         │  - frozen entity dump    │
│  - GET /api/config          │         │  - frozen device dump    │
│  - GET /api/services        │         │  - frozen services dump  │
└──────────────┬──────────────┘         └──────────────┬───────────┘
               │                                       │
               └───────────────┬───────────────────────┘
                               │
                  ┌────────────▼────────────┐
                  │  HA Source Adapter      │
                  │  - unified Entity model │
                  │  - device grouping      │
                  │  - service introspection│
                  └────────────┬────────────┘
                               │
                               ▼
                  ┌─────────────────────────┐
                  │  Integration Grouper    │
                  │  groups entities by     │
                  │  device.manufacturer +  │
                  │  device.model           │
                  └────────────┬────────────┘
                               │
                               ▼  one group → one DDF
                  ┌─────────────────────────┐
                  │  Mapping Engine         │
                  │  ┌───────────────────┐  │
                  │  │ Domain Templates  │  │
                  │  │ - light           │  │
                  │  │ - switch          │  │
                  │  │ - sensor          │  │
                  │  │ - binary_sensor   │  │
                  │  │ - climate         │  │
                  │  │ - cover           │  │
                  │  │ - media_player    │  │
                  │  │ - lock            │  │
                  │  │ - fan             │  │
                  │  │ - vacuum          │  │
                  │  └───────────────────┘  │
                  │           │             │
                  │  ┌────────▼──────────┐  │
                  │  │ DDF Builder       │  │
                  │  │ (uses Sprint-0    │  │
                  │  │  AST classes)     │  │
                  │  └────────┬──────────┘  │
                  └───────────┼─────────────┘
                              │
                              ▼
                  ┌─────────────────────────┐
                  │  Round-Trip Pipeline    │
                  │  ┌────────────────────┐ │
                  │  │ 1. Serializer      │ │
                  │  │    (AST → CSV)     │ │
                  │  ├────────────────────┤ │
                  │  │ 2. Linter (S0)     │ │
                  │  │    must pass clean │ │
                  │  ├────────────────────┤ │
                  │  │ 3. Simulator (S1)  │ │
                  │  │    against synth.  │ │
                  │  │    HA-API capture  │ │
                  │  ├────────────────────┤ │
                  │  │ 4. Test signing    │ │
                  │  └────────────────────┘ │
                  └────────────┬────────────┘
                               │
                               ▼
                       ┌──────────────┐
                       │ Signed DDF   │
                       │ + report     │
                       └──────────────┘
```

**Key design separations:**

- **Source Adapter knows nothing about DDF.** It produces a normalized Python `HAEntity` / `HADevice` model. If we later want a non-HA source (Matter, Zigbee2MQTT direct), only this adapter is replaced.
- **Mapping Engine knows nothing about HTTP.** It takes the normalized HA model and produces an in-memory `DDF` AST (same dataclasses as Sprint 0). Pure transformation, fully unit-testable.
- **Round-Trip Pipeline is the immune system.** Every generated DDF goes through it. If it fails, the generator fails — never silently emit broken output.
- **One DDF per integration family** is the right granularity given the controller's ~30-device limit (Sprint 0 amendments). All Hue lights → one DDF with N items. All Sonoff switches → another DDF. This is what allows the toolkit to scale to real HA instances with 100+ entities.

---

## 6. Module specifications

### 6.1 HA Source Adapter (`ddf_toolkit.bridge.ha_source`)

**Purpose:** Load HA state into a normalized Python model.

**Two backends:**

```python
class HASource(Protocol):
    def load_entities(self) -> list[HAEntity]: ...
    def load_devices(self) -> list[HADevice]: ...
    def load_services(self) -> dict[str, list[HAService]]: ...
    def load_config(self) -> HAConfig: ...

class HALiveSource(HASource):
    """Talks to a real HA instance via REST API."""
    def __init__(self, base_url: str, token: str, timeout: int = 10) -> None: ...

class HASnapshotSource(HASource):
    """Loads a frozen JSON snapshot from disk."""
    def __init__(self, snapshot_path: Path) -> None: ...
```

**Snapshot format** (`tests/fixtures/ha_snapshots/*.json`):

```json
{
  "schema_version": 1,
  "ha_version": "2026.1.4",
  "captured_at": "2026-04-25T10:00:00Z",
  "entities": [...],
  "devices": [...],
  "services": {...},
  "config": {...}
}
```

The snapshot is generated by an `ha snapshot` CLI command (see §8) against a live HA, then committed to the repo as a CI fixture. Snapshots are deterministic; live is allowed to drift.

**Acceptance criteria:**

- Live source connects to Hostinger HA, loads entity catalog in <5s.
- Snapshot source loads fixtures with no network calls.
- Both produce byte-identical normalized models for the same underlying state.
- Authentication errors (bad token, network unreachable) raise clear exceptions, not silent partial loads.
- Unit tests cover both backends with synthetic HA-API responses.

### 6.2 Integration Grouper (`ddf_toolkit.bridge.grouper`)

**Purpose:** Group entities into DDF-sized units.

**Algorithm:**

1. Read all entities + their associated devices.
2. Group entities by `(device.manufacturer, device.model)`. Hue Bridge with 5 lights → one group; Sonoff with 3 switches → another.
3. Within a group, separate entities by domain only if the group exceeds 25 items (under the 30-device controller limit, with headroom).
4. Entities without devices (HA helpers, integrations without device registry entries) are grouped under a synthetic `_unknown` integration.
5. Output: list of `IntegrationGroup` objects, each becoming one DDF.

**Acceptance criteria:**

- Realistic HA snapshot (50+ entities across 5+ integrations) groups correctly.
- No group exceeds 25 items; groups that would, get split by domain.
- Edge case: entity with no device is handled (warning logged, not error).
- Deterministic output: same snapshot always produces same group structure.

### 6.3 Domain Templates (`ddf_toolkit.bridge.templates`)

**Purpose:** One template module per HA domain. Each translates a list of entities of that domain into DDF AST fragments.

**Module layout:**

```
src/ddf_toolkit/bridge/templates/
├── __init__.py             # template registry
├── base.py                 # DomainTemplate ABC
├── light.py
├── switch.py
├── sensor.py
├── binary_sensor.py
├── climate.py
├── cover.py
├── media_player.py
├── lock.py
├── fan.py
└── vacuum.py
```

**Base template contract:**

```python
class DomainTemplate(ABC):
    domain: str

    @abstractmethod
    def can_handle(self, entity: HAEntity) -> bool: ...

    @abstractmethod
    def build_items(self, entities: list[HAEntity]) -> list[Item]: ...

    @abstractmethod
    def build_writes(self, entities: list[HAEntity], services: list[HAService]) -> list[WriteCommand]: ...

    @abstractmethod
    def build_formulas(self, entities: list[HAEntity]) -> list[FormulaDef]: ...
```

**What each template owns:**

| Domain | Read items | Write commands | Notes |
|---|---|---|---|
| `light` | on/off, brightness, color_temp, rgb | `turn_on`, `turn_off`, `toggle` | rgb is optional per device |
| `switch` | on/off | `turn_on`, `turn_off`, `toggle` | simplest domain — start here |
| `sensor` | numeric value, unit | none | read-only |
| `binary_sensor` | bool state | none | read-only |
| `climate` | current_temp, target_temp, mode, fan_mode | `set_temperature`, `set_hvac_mode`, `set_fan_mode` | mode mapping is HA-specific (heat/cool/auto/off) |
| `cover` | position, state | `open_cover`, `close_cover`, `set_cover_position`, `stop_cover` | percentage-based |
| `media_player` | state, volume, source, current_media | `play_media`, `media_play`, `media_pause`, `volume_set` | reduced surface — full media-player has 30+ services, we cover the essential 8 |
| `lock` | locked/unlocked state | `lock`, `unlock` | |
| `fan` | on/off, percentage, oscillating | `turn_on`, `turn_off`, `set_percentage`, `oscillate` | |
| `vacuum` | state, battery_level, fan_speed | `start`, `stop`, `return_to_base` | |

**Acceptance criteria per template:**

- Generates valid DDF AST fragments that pass the Sprint-0 linter (zero errors).
- Items are named by HA `entity_id` with deterministic transformation (e.g., `light.living_room` → `LIGHT_LIVING_ROOM`).
- `*FORMULA` blocks correctly map HA service-call payloads to HA REST API requests.
- Round-trips through the simulator with synthetic HA API captures.
- Each template has at least 5 unit-test cases including edge cases (entity without optional attribute, vendor-specific quirks).

### 6.4 DDF Builder (`ddf_toolkit.bridge.builder`)

**Purpose:** Compose `*GENERAL`, `*CONFIG`, `*ITEM`, `*WRITE`, `*FORMULA`, `*ARGS` sections into a complete DDF AST from template outputs.

**Behaviour:**

- Generates a unique device ID (10x0D-prefixed, following the DeviceLib convention) from a hash of `(manufacturer, model, schema_version)`.
- Sets `*GENERAL` Block 1 with normalized device metadata.
- Sets `*GENERAL` Block 2 with HA REST API connection params (DOMAIN = HA URL, AUTHENTIFICATION = PASSWORD with a `*CONFIG` field for the long-lived token).
- Adds `*CONFIG` fields the user must fill in (HA URL, token, polling interval).
- Composes `*ITEM`, `*WRITE`, `*FORMULA` from template fragments.
- Adds standard utility writes: `GETTOKEN` (if needed for OAuth-style auth), `GETSTATES` (poll all entities at startup and periodic).

**Acceptance criteria:**

- A built DDF parses successfully back through the Sprint-0 parser (round-trip type fidelity).
- Generated device IDs are stable across builds for the same input.
- The DDF lints clean (zero linter errors) for every Top-10 domain.

### 6.5 Round-Trip Pipeline (`ddf_toolkit.bridge.pipeline`)

**Purpose:** Validate every generated DDF against the full toolkit before it's emitted.

**Stages, in order, each must pass:**

1. **Serialize:** AST → CSV bytes via the Sprint-0 serializer (which already exists for signing canonicalization).
2. **Re-parse:** CSV bytes → AST. Compare structurally to the input AST. Detect serialization bugs.
3. **Lint:** Run the full Sprint-0 linter. Zero errors required; warnings logged.
4. **Simulate:** Run against a synthetic HA-API HAR capture. Compare against a golden assertion file. Mismatch fails the build.
5. **Sign with test key:** Verify the signing path works for this DDF.

The pipeline returns a structured `RoundTripReport` with pass/fail per stage and failure details.

**Acceptance criteria:**

- A correctly generated DDF passes all 5 stages.
- An intentionally broken DDF (test fixture: malformed FORMULA, missing ARG) fails with clear stage-attribution.
- Pipeline runs in <10s per DDF on dev laptop (Top-10 domains, ~25 items each).

### 6.6 HA-API HAR Fixtures

For round-trip simulation, we need synthetic HAR captures of HA's REST API. New fixtures:

- `tests/fixtures/captures/ha_states_endpoint.har` — `GET /api/states` returning a realistic mixed-domain entity list (covers all Top-10 domains).
- `tests/fixtures/captures/ha_service_call_light.har` — `POST /api/services/light/turn_on` with payload, returns 200.
- `tests/fixtures/captures/ha_service_call_climate.har` — `POST /api/services/climate/set_temperature`, with realistic body.
- `tests/fixtures/captures/ha_websocket_state_change.har` — incoming state-change event (simulated server-push for `*LISTENER` testing in DDFs that subscribe).
- `tests/fixtures/captures/ha_auth_failure.har` — expired-token scenario.
- `tests/fixtures/captures/ha_partial_unavailable.har` — one entity in `unavailable` state.

**Quality bar (continued from Sprint 1):**

- Realistic JSON shapes against published HA API schema (https://developers.home-assistant.io/docs/api/rest/).
- Edge cases: empty arrays, null fields, error responses, unavailable entities.
- Each entry has a `comment` explaining the scenario.
- Reference URLs cited in `docs/captures-research.md`.

---

## 7. Snapshot tooling

The CLI gains a snapshot capture command. This is how Joe creates fixtures in the first place.

```bash
# Capture a snapshot from a live HA instance
ddf bridge ha snapshot --url http://hostinger-ha:8123 --token <token> -o snapshot.json

# Anonymize a snapshot before committing (strip personal entity_ids, room names)
ddf bridge ha anonymize snapshot.json -o snapshot_anon.json
```

The anonymize step is required for any snapshot committed to a public OSS repo — Martin's living-room light entity IDs should not become public test fixtures.

**Anonymization rules:**

- Replace entity_ids with deterministic pseudonyms (`light.living_room` → `light.location_a`).
- Strip device names, areas, and user-set friendly names.
- Preserve domain, manufacturer, model, supported features.
- Preserve numerical sensor values within reasonable bounds (don't leak presence-by-power-draw).

---

## 8. CLI surface — extensions

New command group `ddf bridge`, joining existing Sprint-0/1 commands.

```bash
# Snapshot lifecycle
ddf bridge ha snapshot --url <url> --token <token> -o <out.json>
ddf bridge ha anonymize <snapshot.json> -o <anon.json>
ddf bridge ha inspect <snapshot.json>          # human-readable summary

# Generation
ddf bridge generate --source <snapshot.json> -o <out_dir>/
ddf bridge generate --source live --url <url> --token <token> -o <out_dir>/
ddf bridge generate --source <snapshot.json> --domain light --domain switch -o <out_dir>/
                                                # filter to specific domains

# Round-trip
ddf bridge validate <generated.csv>            # explicit pipeline run on existing DDF
ddf bridge generate --validate ...             # default: validate every output

# Domain coverage report
ddf bridge coverage <snapshot.json>            # shows: 47 entities, 6 domains in scope, 2 out of scope
```

All `ddf bridge` commands respect the existing `--quiet`, `--verbose`, `--format json` flags from Sprint 0/1.

---

## 9. CI / quality gates

Extends Sprint-0/1 GitHub Actions. Additions:

- New job `bridge-roundtrip-pilots` runs the full Round-Trip Pipeline against three reference snapshots (`tests/fixtures/ha_snapshots/*_anonymized.json`) on every PR.
- Coverage targets: maintain Sprint-1 levels (88% overall), bridge package targets ≥85% (it's pattern-heavy code, some pragmatism allowed).
- New nightly job (cron weekly): runs generator against the live Hostinger HA, compares output to last week's output, alerts on diffs.
- All Sprint-0/1 jobs unchanged.

Claude Code Review Action stays active and reviews bridge-related PRs. Reviewer prompt extension:
> *Additional checks for bridge/ PRs: domain template completeness vs HA service spec; round-trip pipeline coverage; anonymization correctness for any committed snapshots.*

---

## 10. Documentation deliverables

End of Sprint 2:

- `docs/bridge.md` — generator architecture, supported domains, mapping conventions, anonymization rules.
- `docs/bridge-templates.md` — one section per domain explaining the mapping logic (HA service → DDF write).
- `docs/captures-research.md` — extended with HA-API references.
- `docs/cli-reference.md` — extended with `ddf bridge` commands.
- `docs/internal/SPRINT_2_AMENDMENTS.md` — same pattern as Sprint 0/1, captures any reality-vs-PRD findings.
- `CHANGELOG.md` and `pyproject.toml` reflect v0.3.0; tag pushed.

---

## 11. Stretch Goal — Real-Hardware Integration (Joe-gated)

**Trigger condition:** End of Week 2 (Day 10), all of the following must be true to unlock the stretch:

- Generator + Round-Trip Pipeline complete for all Top-10 domains.
- All §11 acceptance criteria green.
- CI green, coverage targets met.
- No P0/P1 bugs open.

**If the gate is not met by Day 10:** stretch is deferred to Sprint 3. Joe finishes the main scope cleanly; the sprint ends on schedule.

**If the gate is met:** Joe selects one HA-controlled hardware device based on availability. Recommended in priority order:

1. **Philips Hue** — well-documented API, local-control mode, push-button auth, fewest moving parts.
2. **Sonoff** (cloud-API only) — simpler hardware, but introduces cloud-dependency for tests.
3. **Aqara** — Zigbee-based, requires Hub.

Any device available to Joe through the Hostinger HA instance qualifies if the above three are unavailable.

**Stretch deliverables (Week 4, ~5 working days):**

- Real-device snapshot captured and anonymized for the chosen integration.
- Generated DDF deployed to a test myGEKKO controller (if available) or simulator with realistic HA traffic.
- End-to-end test: generated DDF controls a real device through the bridge.
- Findings documented in `docs/internal/SPRINT_2_HARDWARE_PILOT.md`.
- Stretch is **explicitly optional**. Failed stretch is not a failed sprint.

---

## 12. Definition of Done — Sprint 2 (main scope, excluding stretch)

The sprint is **done** when *all* of the following are true:

1. ✅ HA Source Adapter works against both live HA (Hostinger) and snapshot files.
2. ✅ Integration Grouper produces deterministic, correctly-sized groups for realistic snapshots.
3. ✅ All ten domain templates implemented, unit-tested, lint-clean.
4. ✅ DDF Builder produces lint-clean, simulator-passable DDFs for all Top-10 domains.
5. ✅ Round-Trip Pipeline implemented; every generated DDF passes all 5 stages.
6. ✅ Six HA-API HAR fixtures exist with golden assertions.
7. ✅ Three reference HA snapshots committed (anonymized) and used in CI.
8. ✅ `ddf bridge generate --source <snapshot> -o <out>/` produces N DDFs for N integration families, all valid.
9. ✅ All CLI commands from §8 work and have help text.
10. ✅ CI green: lint, types, tests ≥88% overall and ≥85% on bridge package.
11. ✅ All docs from §10 exist, accurate, reviewed by Martin.
12. ✅ `CHANGELOG.md` and `pyproject.toml` reflect v0.3.0; tag pushed.
13. ✅ Sprint-2 issues closed referencing the merge commits.

Stretch DoD (only if unlocked, see §11): items 14–17 specified per stretch deliverables.

---

## 13. Risks & open questions

Surface as GitHub issues tagged `question` early.

- **HA service signature drift.** HA's services API changes between versions. A template written for `light.turn_on(brightness=...)` in HA 2026.1 might break if HA changes the signature in 2026.6. Mitigation: pin HA version in CI Docker image; add a "tested against HA versions" matrix in `bridge-templates.md`; surface mismatches as warnings in the coverage command.
- **Long-tail vendor quirks.** HA's `light` domain says brightness is 0–255, but some integrations expose it as 0–100 (percentage) due to hardware limits. Templates need to handle the *intersection* of features supported by the actual entity (HA exposes this via `supported_features` bitmask). Watch for this in the brightness, color, and climate templates particularly.
- **Snapshot anonymization completeness.** A first pass will likely miss leakage paths. Mitigation: code review checklist for any snapshot committed; explicit privacy review of the first three reference snapshots before merge.
- **Round-trip simulator latency.** If validating ten generated DDFs takes 60s on dev laptop, developer feedback loop suffers. Mitigation: parallelize round-trip across DDFs; cache simulator setup between runs.
- **Hostinger HA reliability.** If the test HA instance goes down mid-sprint, live-mode tests fail. Mitigation: snapshot mode as default; live as ancillary. CI uses snapshots only.
- **Real-hardware decision late in sprint.** Joe may want to pre-decide hardware in Week 1 to ensure availability. Acceptable; Joe pings Martin if a specific device requires Martin's hands-on access.

---

## 14. Joe — first reading + estimation request

Same protocol as Sprint 0/1. Before any code:

1. Re-read Sprint-0 and Sprint-1 amendments end-to-end; the AST and interpreter are now production foundations, not theoretical artifacts.
2. Confirm or push back on §5 architecture. Particularly: is "one DDF per integration family" workable, or do edge cases (mixed-vendor groups, devices without device registry entries) force a different granularity?
3. Produce an estimate covering:
   - Total sprint length (in working days)
   - Breakdown by module (source adapter, grouper, each of 10 templates, builder, pipeline, fixtures, CLI, docs)
   - Three highest risks with proposed mitigation
   - Anything in this PRD that contradicts Sprint-0/1 reality or is internally inconsistent
4. Confirm Day 10 stretch gate — agree the criteria are objectively measurable.

Same rule as before: read, think, answer. No code yet. PRD ambiguity gets clarified before Day 1.

---

*End of PRD. Questions to Martin via GitHub issues, not chat.*
