from __future__ import annotations

from typing import Any

from .contracts import JobState, ProductionBrief, StateName

_ALLOWED: dict[StateName, set[StateName]] = {
    "INTAKE": {"AMBIGUITY_REVIEW", "BLOCKED"},
    "AMBIGUITY_REVIEW": {"INTAKE", "BRIEF_LOCKED", "BLOCKED"},
    "BRIEF_LOCKED": {"PLANNING", "INTAKE", "BLOCKED"},
    "PLANNING": {"BUILDING", "INTAKE", "BLOCKED"},
    "BUILDING": {"CRITIQUE", "INTAKE", "BLOCKED"},
    "CRITIQUE": {"VALIDATION", "CORRECTION", "INTAKE", "BLOCKED"},
    "VALIDATION": {"EXPORT", "CORRECTION", "INTAKE", "BLOCKED"},
    "CORRECTION": {"BUILDING", "INTAKE", "BLOCKED"},
    "EXPORT": {"COMPLETE", "CORRECTION", "INTAKE", "BLOCKED"},
    "COMPLETE": set(),
    "BLOCKED": {"INTAKE", "PLANNING", "BUILDING", "CRITIQUE", "VALIDATION", "EXPORT"},
}

BLENDER_STATES: set[StateName] = {"BUILDING", "CRITIQUE", "VALIDATION", "CORRECTION", "EXPORT"}


def transition(job: JobState, target: StateName) -> JobState:
    allowed = _ALLOWED[job.state]
    if target not in allowed:
        raise ValueError(f"illegal workflow transition: {job.state} -> {target}")
    job.state = target
    job.blocked_reason = None if target != "BLOCKED" else job.blocked_reason
    if target == "CORRECTION":
        job.iteration += 1
        job.critic_pass = False
        job.validator_pass = False
    return job


def _brief_dict(brief: ProductionBrief | dict[str, Any]) -> dict[str, Any]:
    return brief.to_dict() if isinstance(brief, ProductionBrief) else brief


def execution_gate_reasons(job: JobState, brief: ProductionBrief | dict[str, Any] | None) -> list[str]:
    reasons: list[str] = []
    if job.state not in BLENDER_STATES:
        reasons.append(f"state {job.state} is not a Blender execution state")
    if job.brief_version <= 0:
        reasons.append("job has no locked brief_version")
    if brief is None:
        reasons.append("brief.current.json is missing")
        return reasons

    payload = _brief_dict(brief)
    if payload.get("status") != "locked":
        reasons.append("current brief is not locked")
    if payload.get("version") != job.brief_version:
        reasons.append("current brief version does not match job state")
    if payload.get("unresolved"):
        reasons.append("current brief still has unresolved requirements")
    if payload.get("contradictions"):
        reasons.append("current brief still has contradictions")
    return reasons


def can_execute_blender(job: JobState, brief: ProductionBrief | dict[str, Any] | None = None) -> bool:
    return not execution_gate_reasons(job, brief)
