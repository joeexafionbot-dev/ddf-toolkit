"""Simulator runner — orchestrate DDF execution against HAR captures.

Implements the trigger-flag execution model discovered in Sprint 0:
1. Initialize interpreter with empty state
2. Run RFORMULA polling cycles to detect initial triggers
3. Loop: find triggered *WRITE, execute its formula, issue HTTP (via HAR),
   run response formula, update state
4. Repeat until no more triggers or step limit reached
5. Return final ITEM/GPARAM state
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from ddf_toolkit.formula.parser import parse_formula
from ddf_toolkit.interpreter.environment import Environment, HttpResponse, WriteState
from ddf_toolkit.interpreter.evaluator import Interpreter
from ddf_toolkit.parser.ast import DDF
from ddf_toolkit.simulator.har_loader import HARLoader


class SimulationError(Exception):
    pass


@dataclass
class SimulationResult:
    """Result of a simulation run."""

    items: dict[int, Any] = field(default_factory=dict)
    gparams: dict[str, Any] = field(default_factory=dict)
    http_requests: list[dict[str, str]] = field(default_factory=list)
    debug_log: list[str] = field(default_factory=list)
    side_effects: dict[str, Any] = field(default_factory=dict)
    steps_executed: int = 0
    step_limit_reached: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "items": {str(k): v for k, v in self.items.items()},
            "gparams": self.gparams,
            "http_requests": self.http_requests,
            "debug_log": self.debug_log,
            "steps_executed": self.steps_executed,
            "step_limit_reached": self.step_limit_reached,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False, default=str)


def run_simulation(
    ddf: DDF,
    loader: HARLoader,
    *,
    step_limit: int = 100,
    frozen_time: float | None = None,
    initial_gparams: dict[str, Any] | None = None,
    initial_config: dict[str, Any] | None = None,
) -> SimulationResult:
    """Run a DDF simulation against HAR-captured traffic.

    Args:
        ddf: Parsed DDF AST
        loader: HAR loader with captured request/response pairs
        step_limit: Max trigger-flag cycles (prevents infinite loops)
        frozen_time: Fixed epoch time for deterministic execution
        initial_gparams: Pre-set GPARAM values (e.g., from prior simulation)
        initial_config: CONFIG values (from *CONFIG section)
    """
    # -- Setup environment --
    env = Environment()

    if frozen_time is not None:
        env.freeze_time(frozen_time)

    if initial_gparams:
        env.gparams.update(initial_gparams)

    # Populate config from DDF *CONFIG section
    if initial_config:
        env.config.update(initial_config)
    for cfg in ddf.config:
        env.config.setdefault(str(cfg.id), "")

    # Register all WRITE commands as WriteStates
    for write in ddf.writes:
        env.write_states[write.alias] = WriteState(alias=write.alias)

    # Register COMMAND aliases too (they can be triggered)
    for cmd in ddf.commands:
        env.write_states[cmd.alias] = WriteState(alias=cmd.alias)

    interp = Interpreter(env, timeout=5.0)

    # -- Run RFORMULA polling pass (initial state setup) --
    for item in ddf.items:
        if item.rformula:
            _exec_safe(interp, item.rformula, env)

    # -- Trigger-flag loop --
    steps = 0
    step_limit_reached = False

    while steps < step_limit:
        # Find first triggered WRITE
        triggered_write = None
        for write in ddf.writes:
            ws = env.write_states.get(write.alias)
            if ws and ws.trigger:
                triggered_write = write
                break

        if triggered_write is None:
            break

        steps += 1
        ws = env.write_states[triggered_write.alias]

        # Issue HTTP request (matched from HAR)
        har_resp = _match_http(loader, triggered_write, env)
        if har_resp is not None:
            ws.http_response = HttpResponse(
                status_code=har_resp.status,
                body=har_resp.body,
                raw_data=har_resp.body_raw,
                url=triggered_write.url or "",
                timestamp=env.now(),
            )
            ws.timestamp = env.now()

            env.http_requests.append(
                {
                    "method": triggered_write.method,
                    "url": triggered_write.url or "",
                    "alias": triggered_write.alias,
                    "status": str(har_resp.status),
                }
            )

        # Execute response formula
        if triggered_write.formula:
            ast = parse_formula(triggered_write.formula)
            if ast.valid and ast.script:
                try:
                    interp.execute_script(ast.script)
                except Exception as e:
                    env.debug_log.append(f"Error in WRITE {triggered_write.alias}: {e}")

        # Reset trigger if formula didn't already
        # (Most formulas end with ALIAS.F := 0)

    else:
        step_limit_reached = True

    # -- Run RFORMULA one more time (final state computation) --
    for item in ddf.items:
        if item.rformula:
            _exec_safe(interp, item.rformula, env)

    return SimulationResult(
        items=dict(env.items),
        gparams=dict(env.gparams),
        http_requests=env.http_requests,
        debug_log=env.debug_log,
        side_effects=dict(env.saved_json),
        steps_executed=steps,
        step_limit_reached=step_limit_reached,
    )


def _exec_safe(interp: Interpreter, formula_src: str, env: Environment) -> None:
    """Execute a formula, catching errors (non-critical in polling passes)."""
    ast = parse_formula(formula_src)
    if ast.valid and ast.script:
        try:
            interp.execute_script(ast.script)
        except Exception as e:
            env.debug_log.append(f"Formula error: {e}")


def _match_http(
    loader: HARLoader,
    write: Any,
    env: Environment,
) -> Any:
    """Try to match a WRITE command's HTTP request in the HAR loader."""
    method = write.method or "GET"
    url = write.url or ""

    # Try domain from GPARAM if URL is relative
    if url and not url.startswith("http"):
        domain = env.gparams.get("DOMAIN", "") or env.get_var(["$", "GPARAM", "DOMAIN"]) or ""
        if domain:
            url = domain.rstrip("/") + "/" + url.lstrip("/")

    # Try exact match first, then relaxed
    resp = loader.match(method, url)
    if resp is None:
        resp = loader.match(method, url, relaxed=True)

    return resp
