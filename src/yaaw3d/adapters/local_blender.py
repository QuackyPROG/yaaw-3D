from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

from yaaw3d.contracts import BuildResult, ExportReport, QAReport


class LocalBlenderAdapter:
    """Local Blender backend shell.

    This adapter runs a user-supplied Blender Python script through a local
    `blender --background` executable. Production tools should grow here
    without weakening the orchestrator's state gates.
    """

    def __init__(self, blender_bin: str = "blender") -> None:
        self.blender_bin = blender_bin

    def _require_blender(self) -> str:
        resolved = shutil.which(self.blender_bin)
        if not resolved:
            raise RuntimeError(f"Blender executable not found: {self.blender_bin}")
        return resolved

    def run_script(self, job_dir: Path, script: Path) -> subprocess.CompletedProcess[str]:
        blender = self._require_blender()
        if not script.exists():
            raise FileNotFoundError(script)
        return subprocess.run(
            [blender, "--background", "--python", str(script)],
            cwd=str(job_dir),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def inspect_scene(self, job_dir: Path) -> dict[str, Any]:
        raise NotImplementedError("local scene inspection requires a Blender Python inspector script")

    def run_milestone(self, job_dir: Path, milestone: dict[str, Any]) -> BuildResult:
        script_value = milestone.get("script")
        if not script_value:
            raise ValueError("local Blender milestone requires a 'script' path")
        proc = self.run_script(job_dir, Path(script_value))
        milestone_id = str(milestone.get("id") or milestone.get("milestone_id") or Path(script_value).stem)
        artifact_id = str(milestone.get("artifact_id") or milestone_id)
        return BuildResult(
            milestone_id=milestone_id,
            artifact_id=artifact_id,
            passed=proc.returncode == 0,
            outputs=[],
            notes=[proc.stdout[-4000:], proc.stderr[-4000:]],
        )

    def capture_views(self, job_dir: Path, views: list[str]) -> list[str]:
        raise NotImplementedError("local viewport capture requires a Blender Python capture script")

    def validate_scene(self, job_dir: Path, checks: list[str]) -> QAReport:
        raise NotImplementedError("local validation requires a Blender Python validator script")

    def export(self, job_dir: Path, export_spec: dict[str, Any]) -> ExportReport:
        raise NotImplementedError("local export requires a Blender Python exporter script")
