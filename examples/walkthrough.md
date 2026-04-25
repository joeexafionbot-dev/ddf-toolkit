# Walkthrough: Parse, Lint, Sign, Verify

This guide walks through the core DDF Toolkit workflow using the Microsoft Calendar pilot DDF.

## Prerequisites

```bash
# From PyPI (when published):
pip install ddf-toolkit

# From a local checkout:
git clone https://github.com/joeexafionbot-dev/ddf-toolkit.git
cd ddf-toolkit
pip install -e .
```

## 1. Parse a DDF

```bash
# Pretty-print the AST as YAML
ddf parse tests/fixtures/ddfs/"Microsoft.Gateway.REST-API (DDF).Calender.1(0x0D00007700010100).csv"

# Or as JSON
ddf parse tests/fixtures/ddfs/"Microsoft.Gateway.REST-API (DDF).Calender.1(0x0D00007700010100).csv" --json
```

## 2. Validate

```bash
ddf validate tests/fixtures/ddfs/"Microsoft.Gateway.REST-API (DDF).Calender.1(0x0D00007700010100).csv"
# Expected: PASS
```

## 3. Lint

```bash
ddf lint tests/fixtures/ddfs/"Microsoft.Gateway.REST-API (DDF).Calender.1(0x0D00007700010100).csv"
# Expected: PASS — no findings

# Machine-readable output for CI
ddf lint tests/fixtures/ddfs/"Microsoft.Gateway.REST-API (DDF).Calender.1(0x0D00007700010100).csv" --format json
```

## 4. Sign with a Test Key

```bash
# Generate a test keypair (one-time)
ddf keygen --test

# Sign the DDF
ddf sign --test tests/fixtures/ddfs/"Microsoft.Gateway.REST-API (DDF).Calender.1(0x0D00007700010100).csv" -o /tmp/signed.csv

# Verify the signature
ddf verify /tmp/signed.csv
# Expected: PASS
```

## What's Next?

- **Sprint 1** will add formula execution and HAR-based simulation
- See [ROADMAP.md](../ROADMAP.md) for the full plan
