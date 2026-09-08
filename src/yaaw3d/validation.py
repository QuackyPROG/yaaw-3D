from __future__ import annotations

from pathlib import Path
from typing import Any

from .questions import BASE_REQUIRED


def require_keys(payload: dict[str, Any], required: list[str], *, name: str) -> None:
    missing = [key for key in required if key not in payload]
    if missing:
        raise ValueError(f"{name} missing required keys: {', '.join(missing)}")


def validate_production_brief(payload: dict[str, Any]) -> None:
    require_keys(
        payload,
        ["job_id", "version", "source_request", "status", "requirements", "unresolved", "contradictions", "acceptance"],
        name="production brief",
    )
    if payload["status"] not in {"draft", "locked"}:
        raise ValueError("production brief status must be draft or locked")
    if not isinstance(payload["version"], int) or payload["version"] < 1:
        raise ValueError("production brief version must be an integer >= 1")
    if not isinstance(payload["requirements"], dict):
        raise ValueError("production brief requirements must be an object")
    if payload["status"] == "locked":
        missing_domains = [qid for qid in BASE_REQUIRED if qid not in payload["requirements"]]
        if missing_domains:
            raise ValueError("locked brief missing base domains: " + ", ".join(missing_domains))
        if payload["unresolved"]:
            raise ValueError("locked brief cannot have unresolved requirements")
        if payload["contradictions"]:
            raise ValueError("locked brief cannot have contradictions")


def validate_job_state(payload: dict[str, Any]) -> None:
    require_keys(
        payload,
        ["job_id", "state", "brief_version", "plan_version", "iteration", "critic_pass", "validator_pass"],
        name="job state",
    )
    allowed = {"INTAKE", "AMBIGUITY_REVIEW", "BRIEF_LOCKED", "PLANNING", "BUILDING", "CRITIQUE", "VALIDATION", "CORRECTION", "EXPORT", "COMPLETE", "BLOCKED"}
    if payload["state"] not in allowed:
        raise ValueError(f"invalid job state: {payload['state']}")


def validate_plan(payload: dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise ValueError("plan must be a JSON object")
    milestones = payload.get("milestones")
    if not isinstance(milestones, list) or not milestones:
        raise ValueError("plan requires a non-empty milestones list")


def validate_existing_files(paths: list[str], *, root: Path | None = None) -> None:
    base = root or Path.cwd()
    missing = [p for p in paths if not (base / p).exists()]
    if missing:
        raise ValueError("referenced files do not exist: " + ", ".join(missing))
