# CLI Reference

## Global Options

All commands support:
- `--verbose / -v` — verbose output
- `--quiet / -q` — suppress non-essential output

Exit codes: `0` success, `1` validation/lint failure, `2` usage error, `3` internal error.

## Commands

### `ddf parse <file.csv>`

Parse a DDF file and print its AST.

```bash
ddf parse device.csv              # YAML output (default)
ddf parse device.csv --json       # JSON output
ddf parse device.csv --format json
```

### `ddf validate <file.csv> [...]`

Schema validation only (pass/fail).

```bash
ddf validate device.csv
ddf validate tests/fixtures/ddfs/*.csv
```

### `ddf lint <file.csv>`

Validate + style/best-practice rules.

```bash
ddf lint device.csv
ddf lint device.csv --format json   # machine-readable output
```

### `ddf formula "<expression>"`

Parse a DDF formula expression (Sprint 0: parse-only, no execution).

```bash
ddf formula "IF X.50 THEN X.60 := 0; ENDIF;"
```

### `ddf simulate <file.csv> --capture <recording.har>`

Run a DDF against captured HAR traffic.

```bash
# Basic simulation
ddf simulate device.csv --capture traffic.har

# With golden-file comparison
ddf simulate device.csv --capture traffic.har --golden expected.json

# With frozen time (deterministic)
ddf simulate device.csv --capture traffic.har --freeze-time 1745571600.0

# Limit trigger-flag cycles
ddf simulate device.csv --capture traffic.har --step-limit 50

# JSON output
ddf simulate device.csv --capture traffic.har --format json
```

### `ddf sign <file.csv>`

Sign a DDF file with ECDSA-SHA384.

```bash
ddf sign device.csv --test -o signed.csv
ddf sign device.csv --key my-key.pem -o signed.csv
```

### `ddf verify <signed.csv>`

Verify a signed DDF file.

```bash
ddf verify signed.csv
ddf verify signed.csv --key custom.pub
```

### `ddf keygen`

Generate an ECDSA P-384 test keypair.

```bash
ddf keygen --test
ddf keygen --test -o ./my-key.pem
```

### `ddf version`

Print version and git SHA.

```bash
ddf version
```
