from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from yaaw3d.contracts import BuildResult, ExportReport, QAReport


class BlenderAdapter(Protocol):
    """Boundary between the workflow kernel and a Blender/MCP implementation."""

    def inspect_scene(self, job_dir: Path) -> dict[str, Any]: ...

    def run_milestone(self, job_dir: Path, milestone: dict[str, Any]) -> BuildResult: ...

    def capture_views(self, job_dir: Path, views: list[str]) -> list[str]: ...

    def validate_scene(self, job_dir: Path, checks: list[str]) -> QAReport: ...

    def export(self, job_dir: Path, export_spec: dict[str, Any]) -> ExportReport: ...
