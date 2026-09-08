from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

from .contracts import Answer, BuildResult, CorrectionTicket, ExportReport, ProductionBrief, QAReport
from .questions import by_id, next_batch, required_ids
from .state_machine import can_execute_blender, execution_gate_reasons, transition
from .storage import append_event, load_state, next_version, read_json, save_state, write_json
from .validation import validate_plan, validate_production_brief

INTAKE_STATES = {"INTAKE", "AMBIGUITY_REVIEW"}


def _current_brief_path(job_dir: Path) -> Path:
    return job_dir / "brief.current.json"


def load_current_brief(job_dir: Path) -> ProductionBrief | None:
    path = _current_brief_path(job_dir)
    if not path.exists():
        return None
    payload = read_json(path)
    validate_production_brief(payload)
    return ProductionBrief(**payload)


def _semantic_payload(brief: ProductionBrief) -> dict[str, Any]:
    return {
        "source_request": brief.source_request,
        "requirements": brief.requirements,
        "unresolved": brief.unresolved,
        "assumptions": brief.assumptions,
        "contradictions": brief.contradictions,
        "acceptance": brief.acceptance,
    }


def _build_brief(job_dir: Path, *, version: int, status: str = "draft") -> ProductionBrief:
    state = load_state(job_dir)
    bank = by_id()
    answers = read_json(job_dir / "answers.json")
    requirements: dict[str, str] = {}
    unresolved: list[str] = []

    for qid in required_ids(answers):
        raw = answers.get(qid)
        if raw is None:
            unresolved.append(qid)
            continue
        answer = Answer(question_id=qid, choice=raw["choice"], custom=raw.get("custom"))
        requirements[qid] = answer.resolved_value(bank[qid])

    for qid, raw in answers.items():
        if qid in requirements:
            continue
        answer = Answer(question_id=qid, choice=raw["choice"], custom=raw.get("custom"))
        requirements[qid] = answer.resolved_value(bank[qid])

    contradictions: list[str] = []
    if requirements.get("animation") == "Rigged/deforming/physics-aware animation" and requirements.get("topology") == "Fast/editable; topology secondary":
        contradictions.append("Deforming animation conflicts with topology being secondary; resolve deformation topology requirements.")

    brief = ProductionBrief(
        job_id=state.job_id,
        version=version,
        source_request=(job_dir / "request.md").read_text(encoding="utf-8").strip(),
        status=status,  # type: ignore[arg-type]
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
    validate_production_brief(brief.to_dict())
    return brief


def _write_brief(job_dir: Path, brief: ProductionBrief, *, event: str) -> None:
    validate_production_brief(brief.to_dict())
    write_json(job_dir / f"brief.v{brief.version}.json", brief)
    write_json(_current_brief_path(job_dir), brief)
    append_event(job_dir, event, {"version": brief.version, "status": brief.status, "unresolved": brief.unresolved, "contradictions": brief.contradictions})


def _ensure_intake_open(job_dir: Path) -> None:
    state = load_state(job_dir)
    if state.state not in INTAKE_STATES:
        raise ValueError("answers are immutable after brief lock; use revise-brief to reopen intake")


def questions_for(job_dir: Path) -> list[dict[str, Any]]:
    answers = read_json(job_dir / "answers.json")
    return [q.to_dict() for q in next_batch(answers, 10)]


def record_answers(job_dir: Path, incoming: dict[str, Any]) -> None:
    _ensure_intake_open(job_dir)
    bank = by_id()
    existing = read_json(job_dir / "answers.json")
    for qid, raw in incoming.items():
        if qid not in bank:
            raise ValueError(f"unknown question id: {qid}")
        if isinstance(raw, str):
            answer = Answer(question_id=qid, choice=raw)
        else:
            answer = Answer(question_id=qid, choice=raw.get("choice", "CUSTOM"), custom=raw.get("custom"))
        answer.resolved_value(bank[qid])
        existing[qid] = {"choice": answer.choice, "custom": answer.custom}
    write_json(job_dir / "answers.json", existing)
    append_event(job_dir, "intake.answers_recorded", {"ids": sorted(incoming)})


def compile_brief(job_dir: Path) -> ProductionBrief:
    _ensure_intake_open(job_dir)
    current = load_current_brief(job_dir)
    candidate = _build_brief(job_dir, version=current.version if current and current.status == "draft" else next_version(job_dir, "brief"))
    if current and current.status == "draft" and _semantic_payload(current) == _semantic_payload(candidate):
        return current
    candidate.version = next_version(job_dir, "brief")
    _write_brief(job_dir, candidate, event="brief.compiled")
    return candidate


def lock_brief(job_dir: Path) -> ProductionBrief:
    state = load_state(job_dir)
    if state.state == "BRIEF_LOCKED":
        current = load_current_brief(job_dir)
        if current is None or current.status != "locked" or current.version != state.brief_version:
            raise ValueError("job state says BRIEF_LOCKED but current brief is missing or inconsistent")
        validate_production_brief(current.to_dict())
        return current
    if state.state not in INTAKE_STATES:
        raise ValueError(f"brief can only lock from intake states, not {state.state}")

    current = load_current_brief(job_dir)
    candidate = _build_brief(job_dir, version=current.version if current and current.status == "draft" else next_version(job_dir, "brief"))
    if not (current and current.status == "draft" and _semantic_payload(current) == _semantic_payload(candidate)):
        _write_brief(job_dir, candidate, event="brief.compiled")
    else:
        candidate = current

    blockers = [*candidate.unresolved, *candidate.contradictions]
    if blockers:
        if state.state == "AMBIGUITY_REVIEW":
            transition(state, "INTAKE")
        save_state(job_dir, state)
        raise ValueError("brief cannot lock: " + "; ".join(blockers))

    if state.state == "INTAKE":
        transition(state, "AMBIGUITY_REVIEW")
    locked = replace(candidate, status="locked")
    validate_production_brief(locked.to_dict())
    state.brief_version = locked.version
    transition(state, "BRIEF_LOCKED")
    _write_brief(job_dir, locked, event="brief.locked")
    save_state(job_dir, state)
    return locked


def revise_brief(job_dir: Path, incoming: dict[str, Any]) -> ProductionBrief:
    state = load_state(job_dir)
    if state.state == "COMPLETE":
        raise ValueError("completed jobs cannot be revised in place; create a new job")
    from_state = state.state
    if state.state not in INTAKE_STATES:
        transition(state, "INTAKE")
        state.plan_version = 0
        state.critic_pass = False
        state.validator_pass = False
        state.blocked_reason = "brief revision invalidated downstream artifacts"
        save_state(job_dir, state)
        append_event(job_dir, "brief.revision_started", {"from_state": from_state})
    record_answers(job_dir, incoming)
    return compile_brief(job_dir)


def require_locked_brief(job_dir: Path) -> ProductionBrief:
    state = load_state(job_dir)
    brief = load_current_brief(job_dir)
    reasons = execution_gate_reasons(replace(state, state="BUILDING"), brief) if brief else ["brief.current.json is missing"]
    reasons = [r for r in reasons if not r.startswith("state ")]
    if reasons:
        raise ValueError("locked brief required: " + "; ".join(reasons))
    assert brief is not None
    return brief


def create_plan(job_dir: Path, plan: dict[str, Any]) -> Path:
    state = load_state(job_dir)
    require_locked_brief(job_dir)
    validate_plan(plan)
    if state.state == "BRIEF_LOCKED":
        transition(state, "PLANNING")
    elif state.state != "PLANNING":
        raise ValueError(f"planning requires BRIEF_LOCKED or PLANNING state, not {state.state}")
    version = next_version(job_dir, "plan")
    state.plan_version = version
    state.critic_pass = False
    state.validator_pass = False
    path = job_dir / f"plan.v{version}.json"
    write_json(path, plan)
    save_state(job_dir, state)
    append_event(job_dir, "plan.created", {"version": version})
    return path


def gate_status(job_dir: Path) -> dict[str, Any]:
    state = load_state(job_dir)
    brief = load_current_brief(job_dir)
    reasons = execution_gate_reasons(state, brief)
    return {"can_execute_blender": not reasons, "reasons": reasons, "state": state.to_dict(), "brief": brief.to_dict() if brief else None}


def begin_build(job_dir: Path) -> None:
    state = load_state(job_dir)
    if state.state != "PLANNING" or not state.plan_version:
        raise ValueError("build requires the planning state and a versioned plan")
    next_state = replace(state)
    transition(next_state, "BUILDING")
    brief = load_current_brief(job_dir)
    if not can_execute_blender(next_state, brief):
        raise ValueError("Blender execution gate failed: " + "; ".join(execution_gate_reasons(next_state, brief)))
    save_state(job_dir, next_state)
    append_event(job_dir, "build.started", {"iteration": next_state.iteration})


def record_build_result(job_dir: Path, result: BuildResult) -> Path:
    state = load_state(job_dir)
    if state.state != "BUILDING":
        raise ValueError("build results can only be recorded in BUILDING state")
    path = job_dir / "build" / f"{result.milestone_id}.iteration-{state.iteration}.json"
    write_json(path, result)
    append_event(job_dir, "build.result_recorded", {"milestone_id": result.milestone_id, "artifact_id": result.artifact_id, "passed": result.passed})
    if not result.passed:
        ticket = CorrectionTicket(
            iteration=state.iteration + 1,
            owner="builder",
            artifact_id=result.artifact_id,
            findings=result.notes or [f"Build milestone {result.milestone_id} failed"],
            required_changes=[f"Resolve build failure in {result.milestone_id}"],
            acceptance_checks=[f"Re-run build milestone {result.milestone_id}"],
        )
        write_json(job_dir / "corrections" / f"iteration-{ticket.iteration}.json", ticket)
        transition(state, "CORRECTION")
        save_state(job_dir, state)
    return path


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

    write_json(job_dir / "qa" / f"{report.domain}.{report.artifact_id}.iteration-{state.iteration}.json", report)

    if not report.passed:
        ticket = CorrectionTicket(
            iteration=state.iteration + 1,
            owner="builder",
            artifact_id=report.artifact_id,
            evidence=report.evidence,
            findings=report.findings,
            required_changes=[f"Resolve: {finding}" for finding in report.findings],
            acceptance_checks=[f"Re-test {report.domain}: {finding}" for finding in report.findings],
        )
        write_json(job_dir / "corrections" / f"iteration-{ticket.iteration}.json", ticket)
        transition(state, "CORRECTION")

    save_state(job_dir, state)
    append_event(job_dir, "qa.recorded", {"domain": report.domain, "passed": report.passed, "artifact_id": report.artifact_id})


def resume_correction(job_dir: Path) -> None:
    state = load_state(job_dir)
    if state.state != "CORRECTION":
        raise ValueError("no correction is pending")
    transition(state, "BUILDING")
    save_state(job_dir, state)
    append_event(job_dir, "build.correction_started", {"iteration": state.iteration})


def record_export(job_dir: Path, report: ExportReport) -> None:
    state = load_state(job_dir)
    if state.state != "EXPORT" or not (state.critic_pass and state.validator_pass):
        raise ValueError("export requires matching visual and technical passes in EXPORT state")
    path = job_dir / "exports" / f"export.{report.artifact_id}.iteration-{state.iteration}.json"
    write_json(path, report)
    append_event(job_dir, "export.recorded", {"artifact_id": report.artifact_id, "passed": report.passed, "files": report.files})
    if report.passed:
        transition(state, "COMPLETE")
    else:
        ticket = CorrectionTicket(
            iteration=state.iteration + 1,
            owner="builder",
            artifact_id=report.artifact_id,
            evidence=report.evidence,
            findings=report.findings,
            required_changes=[f"Resolve export failure: {finding}" for finding in report.findings],
            acceptance_checks=["Re-run export validation"],
        )
        write_json(job_dir / "corrections" / f"iteration-{ticket.iteration}.json", ticket)
        transition(state, "CORRECTION")
    save_state(job_dir, state)


def status_payload(job_dir: Path) -> dict[str, Any]:
    state = load_state(job_dir)
    brief = load_current_brief(job_dir)
    return {"state": state.to_dict(), "brief": brief.to_dict() if brief else None, "gate": gate_status(job_dir)}
