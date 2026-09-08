from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .contracts import BuildResult, ExportReport, QAReport
from .orchestrator import (
    begin_build,
    compile_brief,
    create_plan,
    gate_status,
    lock_brief,
    questions_for,
    record_answers,
    record_build_result,
    record_export,
    record_qa,
    resume_correction,
    revise_brief,
    status_payload,
)
from .storage import create_job

DEFAULT_ROOT = Path(".yaaw3d/jobs")


def _job(path: str) -> Path:
    job = Path(path)
    if not (job / "state.json").exists():
        raise SystemExit(f"not a yaaw-3D job directory: {job}")
    return job


def _read_json(path: str) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"expected JSON object in {path}")
    return payload


def _print(payload: Any) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def cmd_init(args: argparse.Namespace) -> int:
    job = create_job(Path(args.root), args.request)
    print(job)
    _print(questions_for(job))
    return 0


def cmd_questions(args: argparse.Namespace) -> int:
    _print(questions_for(_job(args.job)))
    return 0


def cmd_answer(args: argparse.Namespace) -> int:
    job = _job(args.job)
    record_answers(job, _read_json(args.answers))
    brief = compile_brief(job)
    _print(brief.to_dict())
    return 0


def cmd_revise(args: argparse.Namespace) -> int:
    brief = revise_brief(_job(args.job), _read_json(args.answers))
    _print(brief.to_dict())
    return 0


def cmd_lock(args: argparse.Namespace) -> int:
    brief = lock_brief(_job(args.job))
    _print(brief.to_dict())
    return 0


def cmd_plan(args: argparse.Namespace) -> int:
    path = create_plan(_job(args.job), _read_json(args.plan))
    print(path)
    return 0


def cmd_begin_build(args: argparse.Namespace) -> int:
    begin_build(_job(args.job))
    _print(gate_status(_job(args.job)))
    return 0


def cmd_build_result(args: argparse.Namespace) -> int:
    payload = _read_json(args.result)
    result = BuildResult(
        milestone_id=payload["milestone_id"],
        artifact_id=payload["artifact_id"],
        passed=bool(payload["passed"]),
        outputs=list(payload.get("outputs", [])),
        notes=list(payload.get("notes", [])),
    )
    path = record_build_result(_job(args.job), result)
    print(path)
    return 0


def cmd_qa(args: argparse.Namespace) -> int:
    payload = _read_json(args.report)
    report = QAReport(
        domain=args.domain,
        passed=bool(payload["passed"]),
        findings=list(payload.get("findings", [])),
        artifact_id=str(payload.get("artifact_id", "current")),
        evidence=list(payload.get("evidence", [])),
        scores={str(k): float(v) for k, v in payload.get("scores", {}).items()},
    )
    record_qa(_job(args.job), report)
    _print(status_payload(_job(args.job)))
    return 0


def cmd_resume_correction(args: argparse.Namespace) -> int:
    resume_correction(_job(args.job))
    _print(status_payload(_job(args.job)))
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    payload = _read_json(args.report)
    report = ExportReport(
        artifact_id=str(payload.get("artifact_id", "current")),
        passed=bool(payload["passed"]),
        files=list(payload.get("files", [])),
        evidence=list(payload.get("evidence", [])),
        findings=list(payload.get("findings", [])),
    )
    record_export(_job(args.job), report)
    _print(status_payload(_job(args.job)))
    return 0


def cmd_gate(args: argparse.Namespace) -> int:
    _print(gate_status(_job(args.job)))
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    _print(status_payload(_job(args.job)))
    return 0


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="yaaw3d")
    sub = p.add_subparsers(dest="command", required=True)

    i = sub.add_parser("init", help="create a job and print the first 10-question batch")
    i.add_argument("request")
    i.add_argument("--root", default=str(DEFAULT_ROOT))
    i.set_defaults(func=cmd_init)

    q = sub.add_parser("questions", help="print the next unresolved question batch")
    q.add_argument("job")
    q.set_defaults(func=cmd_questions)

    a = sub.add_parser("answer", help="record structured answers and compile a draft brief")
    a.add_argument("job")
    a.add_argument("answers")
    a.set_defaults(func=cmd_answer)

    r = sub.add_parser("revise-brief", help="explicitly reopen intake and invalidate downstream artifacts")
    r.add_argument("job")
    r.add_argument("answers")
    r.set_defaults(func=cmd_revise)

    l = sub.add_parser("lock", help="lock the production brief if all material requirements pass")
    l.add_argument("job")
    l.set_defaults(func=cmd_lock)

    pl = sub.add_parser("plan", help="record a versioned production plan")
    pl.add_argument("job")
    pl.add_argument("plan")
    pl.set_defaults(func=cmd_plan)

    b = sub.add_parser("begin-build", help="enter BUILDING after the execution gate passes")
    b.add_argument("job")
    b.set_defaults(func=cmd_begin_build)

    br = sub.add_parser("build-result", help="record a Builder milestone result")
    br.add_argument("job")
    br.add_argument("result")
    br.set_defaults(func=cmd_build_result)

    qa = sub.add_parser("qa", help="record visual or technical QA")
    qa.add_argument("job")
    qa.add_argument("domain", choices=["visual", "technical"])
    qa.add_argument("report")
    qa.set_defaults(func=cmd_qa)

    rc = sub.add_parser("resume-correction", help="return from CORRECTION to BUILDING")
    rc.add_argument("job")
    rc.set_defaults(func=cmd_resume_correction)

    ex = sub.add_parser("export", help="record export validation and complete the job on pass")
    ex.add_argument("job")
    ex.add_argument("report")
    ex.set_defaults(func=cmd_export)

    g = sub.add_parser("gate", help="show Blender execution gate status")
    g.add_argument("job")
    g.set_defaults(func=cmd_gate)

    s = sub.add_parser("status", help="show current state, brief, and execution gate")
    s.add_argument("job")
    s.set_defaults(func=cmd_status)

    return p


def main() -> int:
    args = parser().parse_args()
    try:
        return args.func(args)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    raise SystemExit(main())
