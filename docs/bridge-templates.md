# Bridge Domain Templates

One template per HA domain. Each maps HA entities to DDF `*ITEM` and `*WRITE` sections.
All follow the canonical patterns in [bridge.md](bridge.md).

## Template Summary

| Domain | Items/Entity | Services | Value Mapping | Stage 4 |
|--------|-------------|----------|---------------|---------|
| switch | 2 (state + cmd) | turn_on, turn_off | Binary (on→1, off→0) | PASS |
| sensor | 1 (value) | — (read-only) | Pass-through (string/number) | PASS |
| binary_sensor | 1 (bool) | — (read-only) | Binary (on→1, off→0) | PASS |
| lock | 2 (state + cmd) | lock, unlock | Enum (locked→0..jammed→4) | PASS |
| light | 2-4 (state + brightness? + color_temp? + cmd) | turn_on, turn_off | Binary state + pass-through attrs | PASS |
| cover | 3 (state + position + cmd) | open, close, stop | Enum state (closed→0..closing→3) + pass-through position | PASS |
| fan | 3 (state + speed + cmd) | turn_on, turn_off | Binary state + pass-through percentage | PASS |
| climate | 3-4 (temp + setpoint + mode + fan?) | set_temp, set_hvac, set_fan | Enum mode (off→0..fan_only→6) | PASS |
| media_player | 5 (state + vol + src + title + cmd) | 8 transport/volume | Enum state (off→0..standby→4) | PASS |
| vacuum | 4 (state + battery + fan_speed + cmd) | start, stop, return | Enum state (docked→0..error→5) | PASS |

## Value Mapping Rules

See [bridge.md — String-vs-Enum Mapping](bridge.md#string-vs-enum-mapping-pattern).

- **Open domain** (continuous/unbounded values): pass-through as string or number
- **Closed domain** (fixed set of known strings): integer enum via IF/ISEQUAL cascade

## Per-Domain Details

### switch

Simplest domain. Pattern prototype.

- **State item**: ISEQUAL on/off → 1/0
- **Command item**: WFORMULA triggers SVC_TURN_ON (cmd=1) or SVC_TURN_OFF (cmd=2)
- **Writes**: GETSTATES + SVC_TURN_ON + SVC_TURN_OFF

### sensor

Read-only. No service calls.

- **State item**: Pass-through numeric value from `state` field
- **Unit**: from `unit_of_measurement` attribute
- **Writes**: GETSTATES only

### binary_sensor

Read-only boolean.

- **State item**: ISEQUAL on → 1, else → 0
- **Writes**: GETSTATES only

### lock

Binary state + lock/unlock commands.

- **State item**: Enum mapping (locked=0, unlocked=1, locking=2, unlocking=3, jammed=4)
- **Command item**: cmd=1 → SVC_LOCK, cmd=2 → SVC_UNLOCK
- **jammed** (value 4) represents a fault state — logged but no user action possible

### light

Feature-dependent items based on `supported_features` bitmask.

- **State item**: ISEQUAL on/off → 1/0
- **Brightness** (feature bit 1): 0-255 pass-through from `brightness` attribute
- **Color temp** (feature bit 2): mireds pass-through from `color_temp` attribute
- **Command item**: cmd=1 → SVC_LIGHT_TURN_ON, cmd=2 → SVC_LIGHT_TURN_OFF

Not implemented in Sprint 2: RGB color (feature bit 16), effect, transition.

### cover

Position-based with state enum.

- **State item**: Enum (closed=0, open=1, opening=2, closing=3)
- **Position item**: 0-100 pass-through from `current_position`
- **Command item**: cmd=1 → open, cmd=2 → close, cmd=3 → stop

Not implemented: set_cover_position (requires dynamic payload with position value).

### fan

On/off with speed percentage.

- **State item**: ISEQUAL on/off → 1/0
- **Speed item**: 0-100 percentage pass-through
- **Command item**: cmd=1 → turn_on, cmd=2 → turn_off

Not implemented: set_percentage, oscillate (require dynamic payloads).

### climate

Most complex Tier 2 domain. Mode-dependent setpoints.

- **Temperature item**: `current_temperature` pass-through (°C)
- **Setpoint item**: `temperature` (target) with WFORMULA triggering set_temperature
- **Mode item**: Enum (off=0, heat=1, cool=2, auto=3, heat_cool=4, dry=5, fan_only=6)
- **Fan mode item** (conditional): from `fan_modes` attribute list, enum-mapped dynamically

HA-version dependency: `heat_cool` mode added in HA 2024.x. Older versions use `auto` for dual-mode.

### media_player

Largest service surface. Sprint 2 covers essential 8 of 30+ services.

- **State item**: Enum (off=0, idle=1, playing=2, paused=3, standby=4)
- **Volume item**: 0-1 float pass-through
- **Source item**: String pass-through
- **Title item**: String pass-through (`media_title` attribute)
- **Command item**: cmd=1 → play, cmd=2 → pause, cmd=3 → stop

**Why these 8 services:**

| Service | Included | Reason |
|---------|----------|--------|
| media_play | Yes | Core transport |
| media_pause | Yes | Core transport |
| media_stop | Yes | Core transport |
| media_next_track | Yes | Essential navigation |
| media_previous_track | Yes | Essential navigation |
| volume_set | Yes | Volume control |
| volume_up | Yes | Volume control |
| volume_down | Yes | Volume control |
| play_media | No | Requires complex media_content_id/type payload |
| select_source | No | Vendor-specific source lists |
| join/unjoin | No | Multi-room (Sonos-specific) |
| browse_media | No | UI-heavy, no DDF use-case |
| Other 18+ | No | Rare or vendor-specific |

### vacuum

State machine with battery monitoring.

- **State item**: Enum (docked=0, cleaning=1, returning=2, paused=3, idle=4, error=5)
- **Battery item**: 0-100 percentage pass-through
- **Fan speed item**: String pass-through (`standard`, `turbo`, etc.)
- **Command item**: cmd=1 → start, cmd=2 → stop, cmd=3 → return_to_base

**error** state (value 5) indicates a fault — logged, user should check device.

## Known HA Version Dependencies

- `climate.heat_cool` mode: HA 2024.x+
- `media_player.media_announce`: HA 2024.8+ (not implemented)
- `fan.set_percentage` replaced `fan.set_speed` in HA 2021.3+
- `supported_features` bitmask values stable since HA 2023.1
