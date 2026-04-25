# DDF Simulator

The simulator runs a DDF against captured HTTP traffic (HAR files) and reports the resulting state.

## How It Works

```
DDF CSV → Parser → AST
                      ↓
HAR File → Loader → Request/Response Index
                      ↓
              Simulator Runner
              ├── Initialize Environment
              ├── Run RFORMULA pass (initial state)
              ├── Trigger-Flag Loop:
              │   ├── Find triggered *WRITE
              │   ├── Match HTTP from HAR
              │   ├── Execute response formula
              │   └── Update state
              └── Return SimulationResult
```

## Usage

```bash
# Basic simulation
ddf simulate device.csv --capture traffic.har

# With golden-file comparison
ddf simulate device.csv --capture traffic.har --golden expected.json

# With frozen time (deterministic)
ddf simulate device.csv --capture traffic.har --freeze-time 1745571600.0

# JSON output
ddf simulate device.csv --capture traffic.har --format json
```

## HAR Fixture Authoring

HAR files follow the [HAR 1.2 spec](https://w3c.github.io/web-performance/specs/HAR/Overview.html).

### Requirements
- Every entry must have a `comment` explaining the scenario
- JSON response bodies are auto-parsed
- Use `_simulated_event: true` for server-push events (Sprint 2)

### Example Entry
```json
{
  "comment": "OAuth token request",
  "request": {
    "method": "POST",
    "url": "https://login.microsoftonline.com/.../token",
    "headers": [{"name": "Content-Type", "value": "application/x-www-form-urlencoded"}],
    "postData": {"text": "client_id=...&grant_type=client_credentials"}
  },
  "response": {
    "status": 200,
    "headers": [{"name": "Content-Type", "value": "application/json"}],
    "content": {"mimeType": "application/json", "text": "{\"access_token\": \"...\"}"}
  }
}
```

## Golden-File Format

Golden files are JSON with special metadata keys:

```json
{
  "items": {"1": "value", "50": 1.0},
  "_comment": "Description of expected state",
  "_frozen_time": 1745571600.0,
  "_config": {"0": "tenant-id", "1": "client-id", "2": "secret"},
  "_ignore_fields": ["gparams", "debug_log"]
}
```

- Keys starting with `_` are metadata (not compared)
- `_ignore_fields` lists paths to skip in comparison
- Comparison is string-based (`str(expected) == str(actual)`)

## Trigger-Flag Model

See [interpreter.md](interpreter.md) for the full trigger-flag execution model.

Key insight from Sprint 0: `*READ` sections are empty in pilot DDFs. All data fetching uses `*WRITE`
commands triggered by `.F` flags set in `RFORMULA` polling cycles.
