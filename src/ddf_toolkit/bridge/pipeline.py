"""Round-Trip Validation Pipeline for generated DDFs.

Every generated DDF passes through 5 stages before emission.
If any stage fails, the DDF is rejected — never silently emit broken output.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ddf_toolkit.bridge.builder import build_ddf
from ddf_toolkit.bridge.grouper import IntegrationGroup
from ddf_toolkit.linter import lint_ddf
from ddf_toolkit.parser.ast import DDF
from ddf_toolkit.parser.parser import parse_ddf
from ddf_toolkit.serializer import serialize_ddf
from ddf_toolkit.signing.keys import generate_test_keypair
from ddf_toolkit.signing.sign import sign_ddf
from ddf_toolkit.signing.verify import verify_ddf
from ddf_toolkit.simulator.har_loader import HARLoader
from ddf_toolkit.simulator.runner import run_simulation


@dataclass
class StageResult:
    """Result of a single pipeline stage."""

    name: str
    passed: bool
    error: str | None = None
    details: Any = None


@dataclass
class RoundTripReport:
    """Complete pipeline result for one DDF."""

    group_name: str
    stages: list[StageResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(s.passed for s in self.stages)

    @property
    def failed_stage(self) -> str | None:
        for s in self.stages:
            if not s.passed:
                return s.name
        return None

    def summary(self) -> str:
        status = "PASS" if self.passed else f"FAIL at {self.failed_stage}"
        lines = [f"{status}  {self.group_name}"]
        for s in self.stages:
            mark = "PASS" if s.passed else "FAIL"
            lines.append(f"  {mark}  Stage {s.name}")
            if s.error:
                lines.append(f"         {s.error}")
        return "\n".join(lines)


class RoundTripPipeline:
    """5-stage validation pipeline for generated DDFs."""

    def __init__(
        self,
        har_loader: HARLoader | None = None,
        frozen_time: float = 1745571600.0,
        initial_config: dict[str, str] | None = None,
    ) -> None:
        self.har_loader = har_loader
        self.frozen_time = frozen_time
        self.initial_config = initial_config or {
            "0": "http://homeassistant.local:8123",
            "1": "test-ha-token",
            "2": "5000",
        }
        self._tmp_dir = Path("/tmp/ddf-pipeline")
        self._tmp_dir.mkdir(exist_ok=True)

    def validate(
        self,
        group: IntegrationGroup,
        services: dict[str, Any] | None = None,
    ) -> RoundTripReport:
        """Run all 5 stages on a generated DDF."""
        report = RoundTripReport(group_name=group.name)

        # Build DDF
        try:
            ddf_ast = build_ddf(group, services)
        except Exception as e:
            report.stages.append(StageResult(name="build", passed=False, error=str(e)))
            return report

        # Stage 1: Serialize
        csv_text, s1 = self._stage1_serialize(ddf_ast)
        report.stages.append(s1)
        if not s1.passed or csv_text is None:
            return report

        # Stage 2: Re-parse
        reparsed, s2 = self._stage2_reparse(csv_text, group.name)
        report.stages.append(s2)
        if not s2.passed or reparsed is None:
            return report

        # Stage 3: Lint
        s3 = self._stage3_lint(reparsed)
        report.stages.append(s3)
        if not s3.passed:
            return report

        # Stage 4: Simulate
        s4 = self._stage4_simulate(reparsed)
        report.stages.append(s4)

        # Stage 5: Sign
        s5 = self._stage5_sign(csv_text, group.name)
        report.stages.append(s5)

        return report

    def _stage1_serialize(self, ddf: DDF) -> tuple[str | None, StageResult]:
        try:
            csv_text = serialize_ddf(ddf)
            return csv_text, StageResult(name="serialize", passed=True)
        except Exception as e:
            return None, StageResult(name="serialize", passed=False, error=str(e))

    def _stage2_reparse(self, csv_text: str, name: str) -> tuple[DDF | None, StageResult]:
        try:
            safe_name = name.replace(" ", "_").replace("/", "_")
            tmp = self._tmp_dir / f"{safe_name}.csv"
            tmp.write_text(csv_text, encoding="utf-8")
            reparsed = parse_ddf(tmp)
            real_items = [i for i in reparsed.items if i.alias.upper() != "ALIAS"]
            if not real_items:
                return None, StageResult(
                    name="reparse", passed=False, error="No items after re-parse"
                )
            return reparsed, StageResult(name="reparse", passed=True)
        except Exception as e:
            return None, StageResult(name="reparse", passed=False, error=str(e))

    def _stage3_lint(self, ddf: DDF) -> StageResult:
        try:
            findings = lint_ddf(ddf)
            errors = [f for f in findings if f.severity == "error"]
            if errors:
                msgs = "; ".join(f"[{f.code}] {f.message}" for f in errors)
                return StageResult(name="lint", passed=False, error=msgs, details=errors)
            return StageResult(name="lint", passed=True, details=findings)
        except Exception as e:
            return StageResult(name="lint", passed=False, error=str(e))

    def _stage4_simulate(self, ddf: DDF) -> StageResult:
        if self.har_loader is None:
            return StageResult(name="simulate", passed=True, error="skipped (no HAR)")

        try:
            result = run_simulation(
                ddf,
                self.har_loader,
                step_limit=20,
                frozen_time=self.frozen_time,
                initial_config=self.initial_config,
            )
            if result.step_limit_reached:
                return StageResult(name="simulate", passed=False, error="Step limit reached")
            return StageResult(name="simulate", passed=True, details=result)
        except Exception as e:
            return StageResult(name="simulate", passed=False, error=str(e))

    def _stage5_sign(self, csv_text: str, name: str) -> StageResult:
        try:
            safe_name = name.replace(" ", "_").replace("/", "_")
            ddf_path = self._tmp_dir / f"{safe_name}_unsigned.csv"
            ddf_path.write_text(csv_text, encoding="utf-8")

            key_path = self._tmp_dir / "pipeline_key.pem"
            if not key_path.exists():
                generate_test_keypair(output=key_path)

            signed_path = self._tmp_dir / f"{safe_name}_signed.csv"
            sign_ddf(ddf_path, key=key_path, output=signed_path)

            pub_path = key_path.with_suffix(".pub")
            ok = verify_ddf(signed_path, key=pub_path)
            if not ok:
                return StageResult(name="sign", passed=False, error="Verify failed")
            return StageResult(name="sign", passed=True)
        except Exception as e:
            return StageResult(name="sign", passed=False, error=str(e))
