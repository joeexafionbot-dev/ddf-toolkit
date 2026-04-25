# HA-Bridge DDF Generator

Generate DDFs from Home Assistant entities. This document defines the canonical patterns
that ALL domain templates must follow. Read this before writing any template.

## Pattern Anatomy

Every generated DDF has the same structure:

```
*GENERAL (Block 1) — device metadata from HA device registry
*GENERAL (Block 2) — DOMAIN = HA URL, AUTHENTIFICATION = PASSWORD
*CONFIG — 0: HA URL, 1: Bearer Token, 2: Polling Interval (ms)
*COMMAND — manual refresh triggers
*WRITE — GETSTATES (poll), SVC_* (service calls)
*ITEM — state items (read, polled) + command items (write, user-triggered)
*GROUP — one group per entity domain in this DDF
*OBJECT — UI widgets mapping items to display
```

### GETSTATES Write (mandatory in every DDF)

Polls `GET /api/states` to fetch all entity states. Every DDF has exactly one.

```
ALIAS:    GETSTATES
METHOD:   GET
URL:      (built from ARGS)
DATATYPE: JSON
FORMULA:  IF GETSTATES.HTTP_CODE == 200 THEN
              X.200 := 1;
          ELSE
              X.200 := 0;
              DEBUG(GETSTATES.HTTP_DATA);
          ENDIF;
          GETSTATES.F := 0;
ARGS:
  url: /api/states
  header Authorization: $.CONFIG.1 (format: Bearer %s)
```

### SVC_* Writes (one per HA service)

Service calls use `POST /api/services/<domain>/<service>` with JSON body.

```
ALIAS:    SVC_TURN_ON
METHOD:   POST
URL:      (built from ARGS)
DATATYPE: JSON
FORMULA:  IF SVC_TURN_ON.HTTP_CODE == 200 THEN
              DEBUG('Service call OK');
          ELSE IF SVC_TURN_ON.HTTP_CODE == 401 THEN
              DEBUG('Token expired');
              X.201 := 0;
          ELSE
              DEBUG(SVC_TURN_ON.HTTP_DATA);
          ENDIF;
          SVC_TURN_ON.F := 0;
ARGS:
  url: /api/services/switch/turn_on
  header Authorization: $.CONFIG.1 (format: Bearer %s)
  header Content-Type: application/json
  data entity_id: (set dynamically in WFORMULA)
```

## Naming Convention

| Source | DDF Name | Example |
|--------|----------|---------|
| `entity_id` | Alias: `DOMAIN_NAME` | `light.living_room` → `LIGHT_LIVING_ROOM` |
| State item | `{ALIAS}` | `SWITCH_PLUG_A` |
| Command item | `{ALIAS}_CMD` | `SWITCH_PLUG_A_CMD` |
| Service write | `SVC_{SERVICE}` | `SVC_TURN_ON`, `SVC_SET_TEMPERATURE` |

### Collision Handling

Before finalizing item aliases, the builder checks for duplicates. If two entities
produce the same alias (e.g., spaces vs underscores), a numeric suffix is appended:
`SWITCH_PLUG_A`, `SWITCH_PLUG_A_2`.

## RFORMULA/WFORMULA Idioms

### State Item RFORMULA (reading from GETSTATES)

```
IF GETSTATES.HTTP_CODE == 200 THEN
    X.{ALIAS} := GETSTATES.VALUE.{entity_id}.state;
ENDIF;
```

### Command Item WFORMULA (triggering service call)

```
IF X.{ALIAS}_CMD == 1 THEN
    SVC_TURN_ON.F := 1;
ELSE IF X.{ALIAS}_CMD == 2 THEN
    SVC_TURN_OFF.F := 1;
ENDIF;
X.{ALIAS}_CMD := 0;
```

## Error Handling

All WRITE response formulas must handle these HTTP codes:

| Code | Meaning | Action |
|------|---------|--------|
| 200 | Success | Set quality flag `X.200 := 1` |
| 401 | Token expired | Set `X.201 := 0`, log with `DEBUG('Token expired')` |
| 503 | HA unavailable | Set `X.200 := 0`, log with `DEBUG(ALIAS.HTTP_DATA)` |
| Other | Unexpected error | Set `X.200 := 0`, log with `DEBUG(ALIAS.HTTP_DATA)` |

Standard error-handling formula block:

```
IF {ALIAS}.HTTP_CODE == 200 THEN
    X.200 := 1;
ELSE IF {ALIAS}.HTTP_CODE == 401 THEN
    DEBUG('Token expired');
    X.201 := 0;
ELSE
    DEBUG({ALIAS}.HTTP_DATA);
    X.200 := 0;
ENDIF;
{ALIAS}.F := 0;
```

> **`DEBUG()` is a built-in DDF function** (DeviceLib.pdf p.26). It outputs variable names
> and values to the debug TCP port (DEBUGPORT in `*GENERAL`). In test mode, captured to
> `env.debug_log`. It is NOT a placeholder — it is the correct function for runtime logging.

## Config Fields

| ID | Purpose | User-Provided |
|----|---------|---------------|
| 0 | HA Base URL | `http://192.168.1.100:8123` |
| 1 | Bearer Token (long-lived access token) | `eyJ0eXAi...` |
| 2 | Polling Interval (ms) | `5000` |

Token refresh is NOT handled in Sprint 2 DDFs. HA long-lived tokens don't expire.
If the token is invalid (401), the DDF logs the error and sets a quality flag.

## Device-ID Schema

Generated DDFs use the `0xFA` prefix to avoid collision with DeviceLib portal entries:

```
Format: 0x0DFA00<8-hex-hash>0100
Hash:   SHA-256(manufacturer + "|" + model + "|" + schema_version)[:8]
Example: 0x0DFA00A3B7C1D20100
```

## Group Split Rules

- Max 25 items per DDF (controller limit is 30, with 5 headroom)
- If a group exceeds 25: split by HA area
- Fallback: numeric split (items 1-25, 26-50, etc.)

## String-vs-Enum Mapping Pattern

HA entity states fall into two categories:

### Open Value Domain → Pass-Through
State values with unbounded or continuous ranges. Stored as-is (string or number).

Examples: `sensor` temperature (22.5), `sensor` humidity (55), `cover` position (0-100),
`light` brightness (0-255), `light` color_temp (mireds).

RFORMULA: `X.{ALIAS} := GETSTATES.VALUE.{entity_id}.state;`

### Closed Value Domain → Enum-Mapping
State values from a fixed set of known strings. Mapped to integers for `*OBJECT` UI
(TYPE=1 with ENUM/ENUMTEXT/ENUMVAL enables dropdown selection in myGEKKO UI).

| Domain | Field | Values | Enum Mapping |
|--------|-------|--------|--------------|
| `climate` | hvac_mode | off, heat, cool, auto, heat_cool, dry, fan_only | 0-6 |
| `climate` | fan_mode | auto, low, medium, high | 0-3 |
| `cover` | state | closed, open, opening, closing | 0-3 |
| `lock` | state | locked, unlocked, locking, unlocking, jammed | 0-4 |
| `media_player` | state | off, idle, playing, paused, standby | 0-4 |
| `vacuum` | state | docked, cleaning, returning, paused, idle, error | 0-5 |
| `fan` | state | off, on | 0-1 (same as switch) |

RFORMULA pattern for closed-domain states:
```
IF GETSTATES.HTTP_CODE == 200 THEN
    IF ISEQUAL(GETSTATES.VALUE.{entity_id}.state, 'off') THEN
        X.{ALIAS} := 0;
    ELSE IF ISEQUAL(GETSTATES.VALUE.{entity_id}.state, 'heat') THEN
        X.{ALIAS} := 1;
    ELSE IF ISEQUAL(GETSTATES.VALUE.{entity_id}.state, 'cool') THEN
        X.{ALIAS} := 2;
    ENDIF;
ENDIF;
```

**Rule:** If a domain's state is in the table above → use enum mapping.
Otherwise → pass-through.
