from __future__ import annotations

from pathlib import Path
from typing import Any

from yaaw3d.contracts import BuildResult, ExportReport, QAReport
from yaaw3d.storage import write_json


class MockBlenderAdapter:
    """Deterministic adapter used for tests and orchestration dry-runs.

    It does not create geometry. Its output is deliberately labelled as mock
    evidence so it cannot be confused with Blender-authored assets.
    """

    def inspect_scene(self, job_dir: Path) -> dict[str, Any]:
        snapshot = {"backend": "mock", "objects": [], "note": "No Blender scene was opened."}
        write_json(job_dir / "build" / "mock-scene-snapshot.json", snapshot)
        return snapshot

    def run_milestone(self, job_dir: Path, milestone: dict[str, Any]) -> BuildResult:
        milestone_id = str(milestone.get("id") or milestone.get("milestone_id") or "mock-milestone")
        artifact_id = f"mock-{milestone_id}"
        output = job_dir / "build" / f"{artifact_id}.json"
        write_json(output, {"backend": "mock", "milestone": milestone, "artifact_id": artifact_id})
        return BuildResult(milestone_id=milestone_id, artifact_id=artifact_id, passed=True, outputs=[str(output)], notes=["Mock adapter produced orchestration evidence only."])

    def capture_views(self, job_dir: Path, views: list[str]) -> list[str]:
        paths: list[str] = []
        for view in views:
            path = job_dir / "renders" / f"mock-{view}.txt"
            path.write_text(f"mock viewport capture: {view}\n", encoding="utf-8")
            paths.append(str(path))
        return paths

    def validate_scene(self, job_dir: Path, checks: list[str]) -> QAReport:
        return QAReport(domain="technical", passed=True, findings=[], artifact_id="mock-current", evidence=[f"mock-check:{check}" for check in checks])

    def export(self, job_dir: Path, export_spec: dict[str, Any]) -> ExportReport:
        path = job_dir / "exports" / "mock-export.txt"
        path.write_text("mock export; no Blender asset generated\n", encoding="utf-8")
        return ExportReport(artifact_id="mock-current", passed=True, files=[str(path)], evidence=["mock export validation"])
