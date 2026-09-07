# yaaw-3D

**yaaw-3D** is a contract-first agentic workflow for producing Blender assets from underspecified creative requests.

The core rule is simple: **the modeling agent does not get to reinterpret the user's idea.** The user's decisions are captured by an Art Director, compiled into a versioned production brief, and enforced by the rest of the workflow.

## Workflow

```text
USER IDEA
   ↓
ART DIRECTOR
   ↓  10-question batch interview
PRODUCTION BRIEF
   ↓  requirements gate
PLANNER
   ↓
BUILDER
   ↓
CRITIC ──────┐
   ↓         │ correction ticket
VALIDATOR    │
   ↓         │
PASS? ──no───┘
   ↓ yes
EXPORTER
```

### Design principles

- **Understand before building.** Blender execution is blocked until required fields are resolved.
- **Ten questions at a time.** The Art Director asks exactly 10 structured questions per batch: A/B/C, recommendation, and custom answer.
- **Versioned contract.** Every accepted change creates a new `brief.vN.json`; downstream agents read the brief rather than free-form chat.
- **Small agent roster.** Craft knowledge lives in specialist skills, not duplicated personas.
- **Closed-loop verification.** Visual criticism and measurable technical validation are separate gates.
- **Trajectory memory.** Plans, renders, QA reports, corrections, and brief versions are retained per job.
- **Resumable execution.** `state.json` is the durable source of workflow position.

## Quick start

Requires Python 3.11+.

```bash
python -m pip install -e .
yaaw3d init "Create me a soccer ball"
yaaw3d questions .yaaw3d/jobs/<job-id>
yaaw3d answer .yaaw3d/jobs/<job-id> examples/soccer-ball.answers.json
yaaw3d lock .yaaw3d/jobs/<job-id>
yaaw3d status .yaaw3d/jobs/<job-id>
```

`lock` will fail until the required intake contract is complete.

## Repository layout

```text
.codex/config.toml          Codex root/subagent defaults
AGENTS.md                   project-wide operating contract
agents/                     role prompts
skills/                     specialist 3D craft guidance
schemas/                    machine-readable handoff schemas
src/yaaw3d/                 executable state machine + CLI
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
qa/
corrections/
renders/
exports/
```

The runtime deliberately does **not** fabricate Blender tool access. Connect your Blender MCP/tool bridge in the Builder adapter; the workflow contract and gates remain unchanged.

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full design.
