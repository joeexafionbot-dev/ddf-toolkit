# Contributing to DDF Toolkit

## Development Setup

```bash
# Clone
git clone https://github.com/joeexafionbot-dev/ddf-toolkit.git
cd ddf-toolkit

# Create venv
python3.12 -m venv .venv
source .venv/bin/activate

# Install with dev dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

## Running Tests

```bash
pytest                                    # all tests
pytest tests/unit/                        # unit tests only
pytest --cov=ddf_toolkit --cov-report=term-missing  # with coverage
```

## Code Style

- Formatter/linter: [Ruff](https://docs.astral.sh/ruff/)
- Type checker: mypy (strict mode)
- Pre-commit hooks enforce both on every commit

## Commit Messages

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add new linter rule DDF011
fix: correct encoding detection for CP1252 files
docs: update formula-coverage matrix
test: add fixture for empty *READ section
chore: bump ruff to 0.5.0
```

## Pull Requests

- Branch from `main`, PR back to `main`
- Branch naming: `feat/<topic>`, `fix/<topic>`, `docs/<topic>`
- All PRs require review from Martin before merge
- CI must be green (lint + test + build)

## Adding a Linter Rule

1. Add a class in `src/ddf_toolkit/linter/rules.py`
2. Register it in the `RULES` list
3. Add a test in `tests/unit/test_linter.py`
