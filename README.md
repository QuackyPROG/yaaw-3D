# yaaw-3D

**yaaw-3D** is a contract-first agentic workflow for producing Blender assets from underspecified creative requests.

The core rule is simple: **the modeling agent does not get to reinterpret the user's idea.** The user's decisions are captured by an Art Director, compiled into a versioned production brief, locked, and enforced by every downstream phase.

## Workflow

```text
USER IDEA
   ↓
ART DIRECTOR
   ↓  10-question batch interview
PRODUCTION BRIEF
   ↓  immutable lock gate
PLANNER
   ↓
BUILDER / BLENDER ADAPTER
   ↓
CRITIC ──────┐
   ↓         │ correction ticket
VALIDATOR    │
   ↓         │
PASS? ──no───┘
   ↓ yes
EXPORTER
   ↓
COMPLETE
```

## What is implemented

- persisted job state under `.yaaw3d/jobs/<job-id>/`;
- conditional 10-question intake batches;
- draft and locked production briefs;
- immutable post-lock answers, with explicit `revise-brief` reopening;
- downstream invalidation when a locked brief is revised;
- execution gate that checks both state and `brief.current.json`;
- versioned plans;
- build result capture;
- visual and technical QA gates;
- correction tickets tied to artifact IDs and iterations;
- export validation before `COMPLETE`;
- mock and local-Blender adapter boundaries;
- regression tests and GitHub Actions CI.

The runtime still keeps Blender execution behind an adapter boundary. The included mock adapter is for orchestration tests only; it does not create geometry. The local Blender adapter can run Blender Python scripts when Blender is installed, but production-grade modeling/validation tools should be implemented behind the same interface.

## Quick start

Requires Python 3.11+.

```bash
python -m pip install -e .
yaaw3d init "Create me a soccer ball"
yaaw3d questions .yaaw3d/jobs/<job-id>
yaaw3d answer .yaaw3d/jobs/<job-id> examples/soccer-ball.answers.json
yaaw3d lock .yaaw3d/jobs/<job-id>
yaaw3d plan .yaaw3d/jobs/<job-id> examples/simple-plan.json
yaaw3d begin-build .yaaw3d/jobs/<job-id>
yaaw3d qa .yaaw3d/jobs/<job-id> visual examples/visual-pass.json
yaaw3d qa .yaaw3d/jobs/<job-id> technical examples/technical-pass.json
yaaw3d export .yaaw3d/jobs/<job-id> examples/export-pass.json
yaaw3d status .yaaw3d/jobs/<job-id>
```

`lock` fails until all required intake fields are resolved. After lock, `answer` is intentionally blocked. Use `revise-brief` to explicitly reopen intake and invalidate downstream artifacts.

## CLI

```text
yaaw3d init <request>
yaaw3d questions <job>
yaaw3d answer <job> <answers.json>
yaaw3d revise-brief <job> <answers.json>
yaaw3d lock <job>
yaaw3d plan <job> <plan.json>
yaaw3d begin-build <job>
yaaw3d build-result <job> <build-result.json>
yaaw3d qa <job> visual|technical <qa-report.json>
yaaw3d resume-correction <job>
yaaw3d export <job> <export-report.json>
yaaw3d gate <job>
yaaw3d status <job>
```

## Repository layout

```text
.codex/config.toml          Codex root/subagent defaults
.github/workflows/ci.yml    unit-test CI
AGENTS.md                   project-wide operating contract
agents/                     role prompts
skills/                     specialist 3D craft guidance
schemas/                    machine-readable handoff schemas
src/yaaw3d/                 executable state machine + CLI
src/yaaw3d/adapters/        Blender backend boundary
docs/                       architecture and handoff rules
tests/                      gate/state/versioning tests
```

## Runtime artifacts

Each job is stored under `.yaaw3d/jobs/<job-id>/`:

```text
request.md
answers.json
brief.v1.json
brief.current.json
state.json
events.jsonl
plan.vN.json
build/
qa/
corrections/
renders/
exports/
```

Versioned locked briefs are preserved. A revised brief creates a new draft version and invalidates the current plan/QA/export path until it is locked again.
