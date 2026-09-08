# Architecture

## Why this workflow exists

Most Blender agents optimize for "prompt → tool call → visible object." yaaw-3D optimizes for **controlled production**: user intent becomes a contract, execution is staged, and verification is adversarial.

The architecture combines the strongest project research patterns: planner/executor separation, generator↔verifier loops, multi-view inspection, typed Blender operations, workflow-mode/tool filtering, milestone saves, and explicit clarification before construction.

## State machine

```text
INTAKE
  ↓
AMBIGUITY_REVIEW
  ├── unresolved/contradiction ──→ INTAKE
  ↓
BRIEF_LOCKED
  ↓
PLANNING
  ├── material ambiguity ────────→ INTAKE
  ↓
BUILDING
  ↓
CRITIQUE
  ├── fail ─→ CORRECTION ─→ BUILDING
  ↓ pass
VALIDATION
  ├── fail ─→ CORRECTION ─→ BUILDING
  ↓ pass
EXPORT
  ├── fail ─→ CORRECTION ─→ BUILDING
  ↓
COMPLETE
```

A production gate prevents Blender execution until requirements are sufficiently resolved. The gate now checks both durable state and the current brief file:

- state must be a Blender execution state;
- `brief_version` must be non-zero;
- `brief.current.json` must exist;
- the current brief must be `locked`;
- the current brief version must match `state.brief_version`;
- unresolved and contradictions must both be empty.

## Brief integrity

`brief.current.json` is the controlling input after lock. Chat history is supporting context only.

After a brief is locked:

- `answer` is blocked;
- direct mutation requires the explicit `revise-brief` command;
- revision returns the job to `INTAKE`;
- plan, critic pass, validator pass, and export path are invalidated;
- prior locked brief versions remain on disk.

This prevents downstream agents from running against a stale state while the current brief has changed.

## Agent roster

### 1. Art Director

Owns the user-facing requirements interview and the brief. It asks 10 structured questions at a time, records exact decisions, finds contradictions, and creates a new brief version whenever intent changes.

### 2. Planner

Converts the locked brief into build milestones and validation strategy. It may reject an insufficient brief but cannot silently repair it.

### 3. Builder

Executes modeling, lookdev, rigging, animation, and scene work through Blender tools. Detailed craft knowledge is supplied by skills instead of more agents.

### 4. Critic

Uses multi-view visual evidence to assess form, style, materials, presentation, and reference match.

### 5. Validator

Runs deterministic geometry/scene/export checks and returns hard pass/fail.

### 6. Exporter

Packages validated deliverables and records export evidence.

## Blender integration boundary

The workflow kernel deliberately separates orchestration from Blender execution.

`src/yaaw3d/adapters/types.py` defines the adapter contract:

- inspect scene;
- run milestone;
- capture review views;
- validate scene;
- export deliverables.

`MockBlenderAdapter` is for tests and dry-runs only. `LocalBlenderAdapter` is a small shell for running local Blender Python scripts with `blender --background`. A Blender MCP, `bpy` bridge, or native add-on should implement the same interface without weakening the state gates.

Recommended tool families:

- scene inspection;
- mesh/modeling;
- materials/UV;
- rig/animation;
- render/viewport capture;
- technical mesh QA;
- save/export.

Expose tools by workflow phase rather than all at once to reduce selection noise.

## Evaluation

The test suite currently covers:

- exact first 10-question batch;
- conditional follow-up behavior;
- lock failure with unresolved requirements;
- lock idempotency;
- post-lock answer immutability;
- explicit revision invalidation;
- tampered brief gate failure;
- visual/technical QA gates;
- correction-loop ticketing;
- export completion.

Future benchmark work should score visual reference match, mesh technical pass rate, correction-loop convergence, unnecessary user questions, export correctness, and resumability after interruption.
