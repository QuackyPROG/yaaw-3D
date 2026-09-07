from __future__ import annotations

from .contracts import JobState, StateName

_ALLOWED: dict[StateName, set[StateName]] = {
    "INTAKE": {"AMBIGUITY_REVIEW", "BLOCKED"},
    "AMBIGUITY_REVIEW": {"INTAKE", "BRIEF_LOCKED", "BLOCKED"},
    "BRIEF_LOCKED": {"PLANNING"},
    "PLANNING": {"BUILDING", "INTAKE", "BLOCKED"},
    "BUILDING": {"CRITIQUE", "BLOCKED"},
    "CRITIQUE": {"VALIDATION", "CORRECTION", "BLOCKED"},
    "VALIDATION": {"EXPORT", "CORRECTION", "BLOCKED"},
    "CORRECTION": {"BUILDING", "BLOCKED"},
    "EXPORT": {"COMPLETE", "CORRECTION", "BLOCKED"},
    "COMPLETE": set(),
    "BLOCKED": {"INTAKE", "PLANNING", "BUILDING", "CRITIQUE", "VALIDATION", "EXPORT"},
}


def transition(job: JobState, target: StateName) -> JobState:
    allowed = _ALLOWED[job.state]
    if target not in allowed:
        raise ValueError(f"illegal workflow transition: {job.state} -> {target}")
    job.state = target
    if target == "CORRECTION":
        job.iteration += 1
        job.critic_pass = False
        job.validator_pass = False
    return job


def can_execute_blender(job: JobState) -> bool:
    return job.brief_version > 0 and job.state in {
        "PLANNING", "BUILDING", "CRITIQUE", "VALIDATION", "CORRECTION", "EXPORT"
    }
