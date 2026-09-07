from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from .contracts import JobState


def _jsonable(value: Any) -> Any:
    return asdict(value) if is_dataclass(value) else value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(_jsonable(value), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def append_event(job_dir: Path, event: str, payload: dict[str, Any] | None = None) -> None:
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "payload": payload or {},
    }
    with (job_dir / "events.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, sort_keys=True) + "\n")


def create_job(root: Path, request: str) -> Path:
    slug = uuid4().hex[:12]
    job_dir = root / slug
    for child in ("qa", "corrections", "renders", "exports"):
        (job_dir / child).mkdir(parents=True, exist_ok=True)
    (job_dir / "request.md").write_text(request.strip() + "\n", encoding="utf-8")
    write_json(job_dir / "answers.json", {})
    write_json(job_dir / "state.json", JobState(job_id=slug))
    append_event(job_dir, "job.created", {"request": request.strip()})
    return job_dir


def load_state(job_dir: Path) -> JobState:
    return JobState(**read_json(job_dir / "state.json"))


def save_state(job_dir: Path, state: JobState) -> None:
    write_json(job_dir / "state.json", state)


def next_version(job_dir: Path, prefix: str) -> int:
    versions = []
    for path in job_dir.glob(f"{prefix}.v*.json"):
        try:
            versions.append(int(path.stem.split(".v", 1)[1]))
        except (ValueError, IndexError):
            continue
    return max(versions, default=0) + 1
