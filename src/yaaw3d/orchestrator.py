from __future__ import annotations

from pathlib import Path
from typing import Any

from .contracts import Answer, CorrectionTicket, ProductionBrief, QAReport
from .questions import by_id, next_batch
from .state_machine import transition
from .storage import (
    append_event,
    load_state,
    next_version,
    read_json,
    save_state,
    write_json,
)

REQUIRED_INITIAL = {
    "purpose",
    "quality",
    "style",
    "geometry",
    "topology",
    "physical_accuracy",
    "materials",
    "animation",
    "presentation",
    "delivery",
}


def questions_for(job_dir: Path) -> list[dict[str, Any]]:
    answers = read_json(job_dir / "answers.json")
    return [q.to_dict() for q in next_batch(set(answers), 10)]


def record_answers(job_dir: Path, incoming: dict[str, Any]) -> None:
    bank = by_id()
    existing = read_json(job_dir / "answers.json")
    for qid, raw in incoming.items():
        if qid not in bank:
            raise ValueError(f"unknown question id: {qid}")
        if isinstance(raw, str):
            answer = Answer(question_id=qid, choice=raw)
        else:
            answer = Answer(
                question_id=qid,
                choice=raw.get("choice", "CUSTOM"),
                custom=raw.get("custom"),
            )
        # Validation happens by resolving against the canonical question.
        answer.resolved_value(bank[qid])
        existing[qid] = {"choice": answer.choice, "custom": answer.custom}
    write_json(job_dir / "answers.json", existing)
    append_event(job_dir, "intake.answers_recorded", {"ids": sorted(incoming)})


def compile_brief(job_dir: Path) -> ProductionBrief:
    state = load_state(job_dir)
    bank = by_id()
    answers = read_json(job_dir / "answers.json")
    requirements: dict[str, str] = {}
    unresolved: list[str] = []

    for qid in REQUIRED_INITIAL:
        raw = answers.get(qid)
        if raw is None:
            unresolved.append(qid)
            continue
        answer = Answer(question_id=qid, choice=raw["choice"], custom=raw.get("custom"))
        requirements[qid] = answer.resolved_value(bank[qid])

    # Include optional/follow-up answers when present.
    for qid, raw in answers.items():
        if qid in requirements:
            continue
        answer = Answer(question_id=qid, choice=raw["choice"], custom=raw.get("custom"))
        requirements[qid] = answer.resolved_value(bank[qid])

    contradictions: list[str] = []
    if requirements.get("delivery", "").startswith("Game/web") and requirements.get("quality") == "Hero/cinematic":
        contradictions.append("Hero/cinematic quality with a game/web delivery target needs an explicit performance/LOD decision.")
    if requirements.get("animation") == "Rigged/deforming/physics-aware animation" and requirements.get("topology") == "Fast/editable; topology secondary":
        contradictions.append("Deforming animation conflicts with topology being secondary; resolve deformation topology requirements.")

    version = next_version(job_dir, "brief")
    brief = ProductionBrief(
        job_id=state.job_id,
        version=version,
        source_request=(job_dir / "request.md").read_text(encoding="utf-8").strip(),
        requirements=requirements,
        unresolved=sorted(unresolved),
        contradictions=contradictions,
        acceptance={
            "brief_locked_before_blender": True,
            "critic_must_pass": True,
            "validator_must_pass": True,
            "no_non_manifold_geometry": True,
            "no_loose_vertices": True,
            "multi_view_review_required": True,
        },
    )
    write_json(job_dir / f"brief.v{version}.json", brief)
    write_json(job_dir / "brief.current.json", brief)
    append_event(job_dir, "brief.compiled", {"version": version, "unresolved": brief.unresolved, "contradictions": brief.contradictions})
    return brief


def lock_brief(job_dir: Path) -> ProductionBrief:
    state = load_state(job_dir)
    if state.state == "INTAKE":
        transition(state, "AMBIGUITY_REVIEW")
    brief = compile_brief(job_dir)
    blockers = [*brief.unresolved, *brief.contradictions]
    if blockers:
        transition(state, "INTAKE")
        save_state(job_dir, state)
        raise ValueError("brief cannot lock: " + "; ".join(blockers))

    brief.status = "locked"
    write_json(job_dir / f"brief.v{brief.version}.json", brief)
    write_json(job_dir / "brief.current.json", brief)
    state.brief_version = brief.version
    transition(state, "BRIEF_LOCKED")
    save_state(job_dir, state)
    append_event(job_dir, "brief.locked", {"version": brief.version})
    return brief


def create_plan(job_dir: Path, plan: dict[str, Any]) -> Path:
    state = load_state(job_dir)
    if state.state != "BRIEF_LOCKED":
        raise ValueError("planning requires a locked brief")
    transition(state, "PLANNING")
    version = next_version(job_dir, "plan")
    state.plan_version = version
    path = job_dir / f"plan.v{version}.json"
    write_json(path, plan)
    save_state(job_dir, state)
    append_event(job_dir, "plan.created", {"version": version})
    return path


def begin_build(job_dir: Path) -> None:
    state = load_state(job_dir)
    if state.state != "PLANNING" or not state.plan_version:
        raise ValueError("build requires the planning state and a versioned plan")
    transition(state, "BUILDING")
    save_state(job_dir, state)
    append_event(job_dir, "build.started", {"iteration": state.iteration})


def record_qa(job_dir: Path, report: QAReport) -> None:
    state = load_state(job_dir)
    if report.domain == "visual":
        if state.state == "BUILDING":
            transition(state, "CRITIQUE")
        if state.state != "CRITIQUE":
            raise ValueError("visual critique must occur in CRITIQUE")
        state.critic_pass = report.passed
        if report.passed:
            transition(state, "VALIDATION")
    elif report.domain == "technical":
        if state.state != "VALIDATION":
            raise ValueError("technical validation must occur in VALIDATION")
        state.validator_pass = report.passed
        if report.passed and state.critic_pass:
            transition(state, "EXPORT")
    else:
        raise ValueError("reference runtime currently gates on visual and technical QA domains")

    write_json(job_dir / "qa" / f"{report.domain}.iteration-{state.iteration}.json", report)

    if not report.passed:
        ticket = CorrectionTicket(
            iteration=state.iteration + 1,
            owner="builder",
            findings=report.findings,
            required_changes=[f"Resolve: {finding}" for finding in report.findings],
            acceptance_checks=[f"Re-test {report.domain}: {finding}" for finding in report.findings],
        )
        write_json(job_dir / "corrections" / f"iteration-{ticket.iteration}.json", ticket)
        transition(state, "CORRECTION")

    save_state(job_dir, state)
    append_event(job_dir, "qa.recorded", {"domain": report.domain, "passed": report.passed})


def resume_correction(job_dir: Path) -> None:
    state = load_state(job_dir)
    if state.state != "CORRECTION":
        raise ValueError("no correction is pending")
    transition(state, "BUILDING")
    save_state(job_dir, state)
    append_event(job_dir, "build.correction_started", {"iteration": state.iteration})
