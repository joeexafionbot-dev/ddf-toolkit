"""CLI entry point for the ddf command."""

from __future__ import annotations

import importlib.metadata
from pathlib import Path
from typing import Annotated

import typer

app = typer.Typer(
    name="ddf",
    help="DDF Toolkit — parse, validate, lint, and sign myGEKKO DDF files.",
    no_args_is_help=True,
)

# -- Global options ----------------------------------------------------------

_verbose = False
_quiet = False


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


@app.command()
def version() -> None:
    """Print version and exit."""
    v = importlib.metadata.version("ddf-toolkit")
    typer.echo(f"ddf-toolkit {v}")


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

    ddf = parse_ddf(file)
    if json or fmt == "json":
        typer.echo(ddf.to_json())
    else:
        typer.echo(ddf.to_yaml())


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

    errors_found = False
    for file in files:
        try:
            parse_ddf(file)
            if not _quiet:
                typer.echo(f"PASS  {file}")
        except Exception as e:
            errors_found = True
            typer.echo(f"FAIL  {file}: {e}", err=True)
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

    ddf = parse_ddf(file)
    findings = lint_ddf(ddf)
    has_errors = any(f.severity == "error" for f in findings)

    if fmt == "json":
        import json as json_mod

        typer.echo(json_mod.dumps([f.to_dict() for f in findings], indent=2))
    else:
        for f in findings:
            typer.echo(f"{f.severity.upper():7s} [{f.code}] {f.message}")
        if not findings and not _quiet:
            typer.echo(f"PASS  {file} — no findings")

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
    typer.echo(f"Parsed AST: {ast}")
    typer.echo("Note: Execution is not yet implemented (Sprint 1).", err=True)


@app.command()
def simulate(
    file: Annotated[Path, typer.Argument(help="DDF CSV file.")],
    capture: Annotated[Path, typer.Option("--capture", help="HAR capture file.")],
    golden: Annotated[Path | None, typer.Option("--golden", help="Expected output JSON.")] = None,
) -> None:
    """Run a DDF against captured traffic (not yet implemented)."""
    typer.echo("Simulation is not yet implemented (Sprint 1).", err=True)
    raise typer.Exit(code=3)


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
        typer.echo("Provide --key or --test", err=True)
        raise typer.Exit(code=2)

    sign_ddf(file, key=key, test=test, output=output)
    if not _quiet:
        typer.echo(f"Signed: {output or file}")


@app.command()
def verify(
    file: Annotated[Path, typer.Argument(help="Signed DDF CSV file.")],
    key: Annotated[Path | None, typer.Option("--key", help="Public key PEM file.")] = None,
) -> None:
    """Verify a signed DDF file."""
    from ddf_toolkit.signing import verify_ddf

    ok = verify_ddf(file, key=key)
    if ok:
        typer.echo(f"PASS  {file}")
    else:
        typer.echo(f"FAIL  {file}", err=True)
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
    if not _quiet:
        typer.echo(f"Private key: {private_path}")
        typer.echo(f"Public key:  {public_path}")
