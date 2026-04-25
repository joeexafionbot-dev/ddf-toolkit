# Sprint 0 — Status Check vs. Definition of Done

**Date:** 2026-04-25 (after Day 3)
**Reviewer:** Joe (self-audit, strict)

## DoD Item Status

| # | DoD Item (per PRD §10, amended) | Status | Evidence / Gap |
|---|------|--------|----------------|
| 1 | Repo exists on GitHub, public, Apache 2.0, all files from §4 in place | 🟡 PARTIAL | Repo exists (`joeexafionbot-dev/ddf-toolkit`), Apache 2.0 LICENSE present. **Gaps:** `tests/fixtures/captures/` dir missing (deferred per amendment). `tests/fixtures/golden/` dir missing (deferred). `.github/ISSUE_TEMPLATE/` has only `bug.yml` — no feature-request template. |
| 2 | `pip install ddf-toolkit` works from wheel; `ddf --help` shows all §5 commands | 🟡 PARTIAL | Wheel builds successfully. `ddf --help` shows all 9 commands. **Gaps:** `ddf version` does not include git SHA (PRD §5 requires "version + git SHA"). `ddf parse --json` works but `--format json` alias inconsistency not fully tested across all commands. No `--quiet`/`--verbose` behavioral effect on most commands (flags exist but are no-ops except on validate). |
| 3 | `docker run` works from locally built image | ❌ NOT STARTED | Docker is not installed on this machine. Dockerfile exists and CI builds it, but never tested locally. Cannot verify `docker run joeexafionbot-dev/ddf-toolkit ddf --help` works. |
| 4 | Both pilot DDFs parse, lint clean (zero errors) — *amended: no simulate* | ✅ DONE | `ddf validate` PASS on both pilots. `ddf lint` returns zero errors on both (Daikin has 1 warning DDF010 — acceptable per DoD "zero errors, warnings allowed"). Tests: `test_microsoft_calendar_lint_clean`, `test_daikin_stylish_lint_clean`. |
| 5 | `ddf sign --test` round-trips both pilots; `ddf verify` accepts/rejects correctly | ✅ DONE | Tested manually: keygen → sign → verify PASS. Tamper detection verified in `test_tampered_file_fails_verification`. Both pilots: `test_sign_and_verify`, `test_roundtrip_daikin`. |
| 6 | All required CLI commands from §5 exist and behave as specified | 🟡 PARTIAL | All 9 commands exist. **Gaps:** (a) `ddf version` missing git SHA. (b) Exit codes not systematically tested — PRD specifies 0/1/2/3 but only 0 and 1 are tested. (c) `--quiet`/`--verbose` are no-ops on most commands. (d) Color output via `rich` — not implemented (plain `typer.echo` used). (e) `NO_COLOR` env var not respected. (f) `--format json` not implemented on `validate` command. |
| 7 | All linter rules DDF001–DDF010 exist with passing/failing fixtures | ✅ DONE | All 10 rules implemented in `src/ddf_toolkit/linter/rules.py`. Each has pass + fail test in `tests/unit/test_linter.py`. PR #6. |
| 8 | Formula engine parses audited operator set; unsupported raise documented error — *amended: parse-only* | ✅ DONE | Lexer tokenizes all operators from pilot DDFs + DeviceLib.pdf (SWITCH/CASE, FOR, bitwise ops, etc.). `UnsupportedFormulaError` exists and points to `formula-coverage.md`. `parse_formula()` validates syntax. Execution stubbed with `NotImplementedError`. |
| 9 | Six synthetic HAR fixtures — *amended: deferred to Sprint 1* | ✅ N/A | Deferred per SPRINT_0_AMENDMENTS.md. Issue #2 tracks this for Sprint 1. |
| 10 | CI passes: pre-commit clean, pytest >=85% coverage, smoke tests green | 🟡 PARTIAL | CI passes on GitHub Actions (all PRs green). 76 tests, 88% coverage (>85%). **Gaps:** (a) CI smoke test `ddf validate tests/fixtures/ddfs/*.csv` — works but globbing may not match the long filenames with spaces. (b) CI simulate smoke test references files that don't exist (deferred). Should remove or gate that step. |
| 11 | All docs from §9 exist and are reviewed by Martin | 🟡 PARTIAL | Present: `README.md`, `docs/architecture.md`, `docs/ddf-schema.md`, `docs/formula-coverage.md`, `docs/cli-reference.md`, `CONTRIBUTING.md`, `ROADMAP.md`, `CHANGELOG.md`. **Gaps:** (a) Martin has not formally reviewed docs (no PR comment/approval on docs). (b) `docs/ddf-schema.md` has `// AMBIGUOUS` items pending Martin's confirmation. |
| 12 | Walkthrough in `examples/walkthrough.md` runs end-to-end — *amended: no simulate* | 🟡 PARTIAL | Walkthrough covers parse → validate → lint → keygen → sign → verify. Manually verified each step works. **Gap:** Not tested as a scripted end-to-end run from fresh checkout (requires `pip install -e .` first, which the walkthrough says `pip install ddf-toolkit` — won't work until published to PyPI). |

## Summary

| Status | Count | Items |
|--------|-------|-------|
| ✅ DONE | 4 | #4, #5, #7, #8 |
| ✅ N/A (deferred) | 1 | #9 |
| 🟡 PARTIAL | 6 | #1, #2, #3, #6, #10, #11, #12 |
| ❌ NOT STARTED | 1 | #3 (Docker local test) |

## Concrete Gaps to Close

### Must-fix (blocks Sprint 0 completion)

1. **`ddf version` needs git SHA** — PRD §5 explicitly requires it
2. **CLI `--quiet`/`--verbose` must have observable behavior** — at minimum suppress/show progress output
3. **Color output via `rich`** — PRD §5 cross-cutting requirement: "Color output via `rich`, auto-disabled when not a TTY or when `NO_COLOR` env set"
4. **Exit codes 2 and 3** — need to be systematically applied (2=usage error, 3=internal error)
5. **CI workflow** — remove the `ddf simulate` smoke test step (deferred to Sprint 1)
6. **`--format json` on `validate` command** — currently accepted but ignored
7. **Walkthrough** — should use `pip install -e .` or `pip install .` for local checkout

### Should-fix (quality gaps)

8. **Docker local test** — need Docker installed or CI-only verification accepted
9. **Lint JSON Schema** — PRD §6.2 says "--format json output validates against a published JSON Schema in docs/" — no JSON Schema exists
10. **Martin's doc review** — formal sign-off needed on docs

### Nice-to-have (won't block DoD)

11. Feature request issue template
12. `ddf parse --format yaml` explicit option (currently default)
