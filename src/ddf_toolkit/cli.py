"""CLI entry point for the ddf command."""

from __future__ import annotations

import importlib.metadata
import json as json_mod
import os
import subprocess
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

app = typer.Typer(
    name="ddf",
    help="DDF Toolkit — parse, validate, lint, and sign myGEKKO DDF files.",
    no_args_is_help=True,
)

# Rich console respects NO_COLOR env and non-TTY
_console = Console(
    highlight=False,
    no_color=os.environ.get("NO_COLOR") is not None,
)
_err_console = Console(
    stderr=True,
    highlight=False,
    no_color=os.environ.get("NO_COLOR") is not None,
)

# -- Global options ----------------------------------------------------------

_verbose = False
_quiet = False


def _info(msg: str) -> None:
    """Print info message (suppressed by --quiet)."""
    if not _quiet:
        _console.print(msg)


def _verbose_msg(msg: str) -> None:
    """Print verbose message (only with --verbose)."""
    if _verbose:
        _err_console.print(f"[dim]{msg}[/dim]")


def _error(msg: str) -> None:
    """Print error message to stderr."""
    _err_console.print(f"[red]{msg}[/red]")


def _success(msg: str) -> None:
    """Print success message."""
    if not _quiet:
        _console.print(f"[green]{msg}[/green]")


def _warning(msg: str) -> None:
    """Print warning message."""
    _console.print(f"[yellow]{msg}[/yellow]")


@app.callback()
def main(
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Verbose output.")] = False,
    quiet: Annotated[
        bool, typer.Option("--quiet", "-q", help="Suppress non-essential output.")
    ] = False,
) -> None:
    global _verbose, _quiet  # noqa: PLW0603
    _verbose = verbose
    _quiet = quiet


# -- Commands ----------------------------------------------------------------


def _git_sha() -> str:
    """Get short git SHA, or empty string if not in a git repo."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return ""


@app.command()
def version() -> None:
    """Print version and git SHA."""
    v = importlib.metadata.version("ddf-toolkit")
    sha = _git_sha()
    if sha:
        _console.print(f"ddf-toolkit {v} ({sha})")
    else:
        _console.print(f"ddf-toolkit {v}")


@app.command()
def parse(
    file: Annotated[Path, typer.Argument(help="Path to DDF CSV file.")],
    json: Annotated[bool, typer.Option("--json", help="Output AST as JSON.")] = False,
    fmt: Annotated[
        str | None,
        typer.Option("--format", "-f", help="Output format: json or yaml."),
    ] = None,
) -> None:
    """Parse a DDF file and print its AST."""
    from ddf_toolkit.parser import parse_ddf

    _verbose_msg(f"Parsing {file}")
    try:
        ddf = parse_ddf(file)
    except Exception as e:
        _error(f"Parse error: {e}")
        raise typer.Exit(code=3) from e

    if json or fmt == "json":
        _console.print(ddf.to_json())
    else:
        _console.print(ddf.to_yaml())


@app.command()
def validate(
    files: Annotated[list[Path], typer.Argument(help="DDF CSV file(s) to validate.")],
    fmt: Annotated[
        str | None,
        typer.Option("--format", "-f", help="Output format: json or text."),
    ] = None,
) -> None:
    """Validate DDF file(s) against the schema."""
    from ddf_toolkit.parser import parse_ddf

    results: list[dict[str, str]] = []
    errors_found = False

    for file in files:
        _verbose_msg(f"Validating {file}")
        try:
            parse_ddf(file)
            results.append({"file": str(file), "status": "PASS"})
            _success(f"PASS  {file}")
        except Exception as e:
            errors_found = True
            results.append({"file": str(file), "status": "FAIL", "error": str(e)})
            _error(f"FAIL  {file}: {e}")

    if fmt == "json":
        _console.print(json_mod.dumps(results, indent=2))

    if errors_found:
        raise typer.Exit(code=1)


@app.command()
def lint(
    file: Annotated[Path, typer.Argument(help="DDF CSV file to lint.")],
    fmt: Annotated[
        str | None,
        typer.Option("--format", "-f", help="Output format: json or text."),
    ] = None,
) -> None:
    """Validate and lint a DDF file."""
    from ddf_toolkit.linter import lint_ddf
    from ddf_toolkit.parser import parse_ddf

    _verbose_msg(f"Linting {file}")
    try:
        ddf = parse_ddf(file)
    except Exception as e:
        _error(f"Parse error: {e}")
        raise typer.Exit(code=3) from e

    findings = lint_ddf(ddf)
    has_errors = any(f.severity == "error" for f in findings)

    if fmt == "json":
        _console.print(json_mod.dumps([f.to_dict() for f in findings], indent=2))
    else:
        for f in findings:
            if f.severity == "error":
                _error(f"ERROR   [{f.code}] {f.message}")
            elif f.severity == "warning":
                _warning(f"WARNING [{f.code}] {f.message}")
            else:
                _info(f"INFO    [{f.code}] {f.message}")
        if not findings:
            _success(f"PASS  {file} — no findings")

    if has_errors:
        raise typer.Exit(code=1)


@app.command()
def formula(
    expression: Annotated[str, typer.Argument(help="Formula expression to evaluate.")],
    context: Annotated[
        Path | None,
        typer.Option("--context", help="JSON file with evaluation context."),
    ] = None,
) -> None:
    """Evaluate a DDF formula expression (parse-only in Sprint 0)."""
    from ddf_toolkit.formula import parse_formula

    ast = parse_formula(expression)
    _console.print(f"Parsed AST: {ast}")
    _warning("Note: Execution is not yet implemented (Sprint 1).")


@app.command()
def simulate(
    file: Annotated[Path, typer.Argument(help="DDF CSV file.")],
    capture: Annotated[Path, typer.Option("--capture", help="HAR capture file.")],
    golden: Annotated[Path | None, typer.Option("--golden", help="Expected output JSON.")] = None,
    step_limit: Annotated[int, typer.Option("--step-limit", help="Max trigger-flag cycles.")] = 100,
    freeze_time: Annotated[
        str | None,
        typer.Option("--freeze-time", help="Frozen epoch time (float or ISO)."),
    ] = None,
    fmt: Annotated[
        str | None,
        typer.Option("--format", "-f", help="Output format: json or text."),
    ] = None,
) -> None:
    """Run a DDF against captured HAR traffic."""
    from ddf_toolkit.parser import parse_ddf
    from ddf_toolkit.simulator.har_loader import HARLoader
    from ddf_toolkit.simulator.runner import run_simulation

    _verbose_msg(f"Simulating {file} against {capture}")
    try:
        ddf = parse_ddf(file)
        loader = HARLoader.from_file(capture)
    except Exception as e:
        _error(f"Load error: {e}")
        raise typer.Exit(code=3) from e

    frozen = float(freeze_time) if freeze_time else None
    result = run_simulation(ddf, loader, step_limit=step_limit, frozen_time=frozen)

    if fmt == "json":
        _console.print(result.to_json())
    else:
        _info(f"Steps: {result.steps_executed}")
        _info(f"Items set: {len(result.items)}")
        if result.step_limit_reached:
            _warning("Step limit reached!")

    if golden:
        from ddf_toolkit.golden.runner import run_golden_test

        gr = run_golden_test(
            ddf_path=file,
            capture_path=capture,
            golden_path=golden,
            frozen_time=frozen,
        )
        if gr.passed:
            _success("Golden: PASS")
        else:
            _error("Golden: FAIL")
            for d in gr.diffs[:10]:
                _error(f"  {d.path}: expected={d.expected!r}, got={d.actual!r}")
            raise typer.Exit(code=1)


@app.command()
def sign(
    file: Annotated[Path, typer.Argument(help="DDF CSV file to sign.")],
    key: Annotated[Path | None, typer.Option("--key", help="Private key PEM file.")] = None,
    test: Annotated[bool, typer.Option("--test", help="Use bundled test key.")] = False,
    output: Annotated[
        Path | None,
        typer.Option("-o", "--output", help="Output signed file path."),
    ] = None,
) -> None:
    """Sign a DDF file with ECDSA-SHA384."""
    from ddf_toolkit.signing import sign_ddf

    if not key and not test:
        _error("Provide --key or --test")
        raise typer.Exit(code=2)

    _verbose_msg(f"Signing {file}")
    try:
        sign_ddf(file, key=key, test=test, output=output)
    except Exception as e:
        _error(f"Signing failed: {e}")
        raise typer.Exit(code=3) from e

    _success(f"Signed: {output or file}")


@app.command()
def verify(
    file: Annotated[Path, typer.Argument(help="Signed DDF CSV file.")],
    key: Annotated[Path | None, typer.Option("--key", help="Public key PEM file.")] = None,
) -> None:
    """Verify a signed DDF file."""
    from ddf_toolkit.signing import verify_ddf

    _verbose_msg(f"Verifying {file}")
    try:
        ok = verify_ddf(file, key=key)
    except Exception as e:
        _error(f"Verification error: {e}")
        raise typer.Exit(code=3) from e

    if ok:
        _success(f"PASS  {file}")
    else:
        _error(f"FAIL  {file}")
        raise typer.Exit(code=1)


@app.command()
def keygen(
    test: Annotated[bool, typer.Option("--test", help="Generate test keypair.")] = True,
    output: Annotated[
        Path | None,
        typer.Option("-o", "--output", help="Output path for private key."),
    ] = None,
) -> None:
    """Generate an ECDSA P-384 keypair for development."""
    from ddf_toolkit.signing import generate_test_keypair

    private_path, public_path = generate_test_keypair(output=output)
    _success(f"Private key: {private_path}")
    _success(f"Public key:  {public_path}")


# -- Bridge commands ---------------------------------------------------------

bridge_app = typer.Typer(name="bridge", help="HA-Bridge DDF Generator.")
app.add_typer(bridge_app)


@bridge_app.command("generate")
def bridge_generate(
    source: Annotated[Path, typer.Option("--source", help="HA snapshot JSON file.")],
    output: Annotated[
        Path, typer.Option("-o", "--output", help="Output directory for generated DDFs.")
    ] = Path("output"),
    domain: Annotated[
        list[str] | None,
        typer.Option("--domain", help="Filter to specific domain(s)."),
    ] = None,
    no_validate: Annotated[
        bool,
        typer.Option("--no-validate", help="Skip round-trip validation."),
    ] = False,
    fmt: Annotated[
        str | None,
        typer.Option("--format", "-f", help="Output format: json or text."),
    ] = None,
) -> None:
    """Generate DDFs from an HA snapshot."""
    from ddf_toolkit.bridge.builder import build_ddf
    from ddf_toolkit.bridge.grouper import group_entities
    from ddf_toolkit.bridge.ha_source import HASnapshotSource
    from ddf_toolkit.bridge.pipeline import RoundTripPipeline
    from ddf_toolkit.bridge.templates import get_template
    from ddf_toolkit.serializer import serialize_ddf
    from ddf_toolkit.simulator.har_loader import HARLoader

    snapshot = HASnapshotSource(source).load()
    groups = group_entities(snapshot)
    output.mkdir(parents=True, exist_ok=True)

    if no_validate:
        _warning("--no-validate: skipping round-trip validation")

    # Load HAR for pipeline if validating
    pipeline = None
    if not no_validate:
        har_path = Path("tests/fixtures/captures/ha_states_endpoint.har")
        loader = HARLoader.from_file(har_path) if har_path.exists() else None
        pipeline = RoundTripPipeline(har_loader=loader)

    results = []
    for group in groups:
        # Filter by domain if specified
        if domain:
            domains_in_group = {e.domain for e in group.entities}
            if not domains_in_group.intersection(set(domain)):
                continue

        # Check if any template exists
        has_template = any(get_template(e.domain) for e in group.entities)
        if not has_template:
            _verbose_msg(f"Skipping {group.name} (no supported domains)")
            continue

        _verbose_msg(f"Generating {group.name}")

        if pipeline and not no_validate:
            report = pipeline.validate(group, snapshot.services)
            if not report.passed:
                _error(f"FAIL  {group.name} at {report.failed_stage}")
                results.append(
                    {"group": group.name, "status": "FAIL", "stage": report.failed_stage}
                )
                continue
            _success(f"PASS  {group.name} (all 5 stages)")

        # Build and write
        ddf = build_ddf(group, snapshot.services)
        csv = serialize_ddf(ddf)
        safe_name = group.name.replace(" ", "_").replace("/", "_").lower()
        out_file = output / f"{safe_name}.csv"
        out_file.write_text(csv, encoding="utf-8")
        results.append({"group": group.name, "status": "OK", "file": str(out_file)})
        _info(f"  → {out_file}")

    if fmt == "json":
        import json as json_mod

        _console.print(json_mod.dumps(results, indent=2))
    else:
        _info(f"\nGenerated {len([r for r in results if r.get('status') == 'OK'])} DDFs")


@bridge_app.command("inspect")
def bridge_inspect(
    source: Annotated[Path, typer.Argument(help="HA snapshot JSON file.")],
) -> None:
    """Show summary of an HA snapshot."""
    from ddf_toolkit.bridge.grouper import group_entities
    from ddf_toolkit.bridge.ha_source import HASnapshotSource
    from ddf_toolkit.bridge.templates import supported_domains

    snapshot = HASnapshotSource(source).load()
    groups = group_entities(snapshot)

    _info(f"HA Version: {snapshot.ha_version}")
    _info(f"Entities: {len(snapshot.entities)}")
    _info(f"Devices: {len(snapshot.devices)}")
    _info(f"Groups: {len(groups)}")
    _info("")

    supported = set(supported_domains())
    for group in groups:
        domains = {e.domain for e in group.entities}
        in_scope = domains & supported
        out_scope = domains - supported
        _info(f"  {group.name}: {len(group.entities)} entities")
        if in_scope:
            _success(f"    Supported: {', '.join(sorted(in_scope))}")
        if out_scope:
            _warning(f"    Unsupported: {', '.join(sorted(out_scope))}")


@bridge_app.command("coverage")
def bridge_coverage(
    source: Annotated[Path, typer.Argument(help="HA snapshot JSON file.")],
) -> None:
    """Show domain coverage for an HA snapshot."""
    from collections import Counter

    from ddf_toolkit.bridge.ha_source import HASnapshotSource
    from ddf_toolkit.bridge.templates import supported_domains

    snapshot = HASnapshotSource(source).load()
    supported = set(supported_domains())

    domain_counts: Counter[str] = Counter(e.domain for e in snapshot.entities)
    total = len(snapshot.entities)
    in_scope = sum(c for d, c in domain_counts.items() if d in supported)
    out_scope = total - in_scope

    _info(f"Total entities: {total}")
    _success(f"In scope: {in_scope} ({in_scope * 100 // total}%)")
    if out_scope:
        _warning(f"Out of scope: {out_scope} ({out_scope * 100 // total}%)")
    _info("")

    for domain, count in domain_counts.most_common():
        status = "SUPPORTED" if domain in supported else "unsupported"
        _info(f"  {domain:20s} {count:3d} entities  [{status}]")
