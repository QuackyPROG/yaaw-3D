from __future__ import annotations

import argparse
import json
from pathlib import Path

from .orchestrator import compile_brief, lock_brief, questions_for, record_answers
from .storage import create_job, load_state, read_json

DEFAULT_ROOT = Path(".yaaw3d/jobs")


def _job(path: str) -> Path:
    job = Path(path)
    if not (job / "state.json").exists():
        raise SystemExit(f"not a yaaw-3D job directory: {job}")
    return job


def cmd_init(args: argparse.Namespace) -> int:
    job = create_job(Path(args.root), args.request)
    print(job)
    print(json.dumps(questions_for(job), indent=2))
    return 0


def cmd_questions(args: argparse.Namespace) -> int:
    print(json.dumps(questions_for(_job(args.job)), indent=2))
    return 0


def cmd_answer(args: argparse.Namespace) -> int:
    job = _job(args.job)
    incoming = json.loads(Path(args.answers).read_text(encoding="utf-8"))
    record_answers(job, incoming)
    brief = compile_brief(job)
    print(json.dumps(brief.to_dict(), indent=2))
    return 0


def cmd_lock(args: argparse.Namespace) -> int:
    brief = lock_brief(_job(args.job))
    print(json.dumps(brief.to_dict(), indent=2))
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    job = _job(args.job)
    state = load_state(job).to_dict()
    brief_path = job / "brief.current.json"
    payload = {"state": state, "brief": read_json(brief_path) if brief_path.exists() else None}
    print(json.dumps(payload, indent=2))
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

    l = sub.add_parser("lock", help="lock the production brief if all material requirements pass")
    l.add_argument("job")
    l.set_defaults(func=cmd_lock)

    s = sub.add_parser("status", help="show current state and brief")
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
