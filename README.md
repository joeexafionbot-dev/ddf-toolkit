# ddf-toolkit

Python toolkit for myGEKKO DDF (Device Definition File) artifacts — parse, validate, lint, and sign.

## What is DDF?

DDF (Device Definition File) is the file format used by [myGEKKO](https://www.my-gekko.com/) building automation controllers to define device integrations. A DDF describes how a controller communicates with external devices via REST APIs, Modbus, or serial protocols.

## Install

```bash
pip install ddf-toolkit
```

Or with Docker:

```bash
docker run joeexafionbot-dev/ddf-toolkit ddf --help
```

## Quick Start

```bash
# Parse a DDF file and inspect its structure
ddf parse device.csv

# Validate a DDF file
ddf validate device.csv

# Lint with best-practice rules
ddf lint device.csv

# Generate a test keypair and sign
ddf keygen --test
ddf sign --test device.csv -o signed.csv
ddf verify signed.csv
```

## Development

```bash
git clone https://github.com/joeexafionbot-dev/ddf-toolkit.git
cd ddf-toolkit
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pre-commit install
pytest
```

## Documentation

- [Architecture](docs/architecture.md)
- [DDF Schema Reference](docs/ddf-schema.md)
- [Formula Coverage](docs/formula-coverage.md)
- [CLI Reference](docs/cli-reference.md)

## License

Apache 2.0 — see [LICENSE](LICENSE)
