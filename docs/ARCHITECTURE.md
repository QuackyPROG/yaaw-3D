# Architecture

## Why this workflow exists

Most Blender agents optimize for "prompt → tool call → visible object." yaaw-3D optimizes for **controlled production**: user intent becomes a contract, execution is staged, and verification is adversarial.

The architecture combines the strongest patterns from the project research: planner/executor separation, generator↔verifier loops, multi-view inspection, typed Blender operations, workflow-mode/tool filtering, milestone saves, and explicit clarification before construction.

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

A production gate prevents Blender execution until requirements are sufficiently resolved; this is a first-class state transition, not a sentence in a prompt.

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

## Production contract

`brief.current.json` is the controlling input after lock. Chat history is supporting context only. This prevents downstream agents from "helpfully" changing user decisions.

Each brief version records:
- source request;
- normalized requirements;
- unresolved decisions;
- explicit assumptions;
- contradictions;
- acceptance checks;
- lock status.

## Trajectory memory

The system persists the *production trajectory*, not merely a conversational memory. Per job it retains:
- all brief versions;
- plans;
- build milestones;
- visual evidence;
- QA reports;
- correction tickets;
- event log;
- exports.

This lets a verifier know what previous iterations attempted and lets interrupted jobs resume from `state.json`.

## Blender integration boundary

The current reference runtime intentionally stops at a typed orchestration boundary. A Blender MCP, `bpy` bridge, or native addon should implement Builder/Validator tool calls without weakening the state gates.

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

A future benchmark suite should score:
- intake completeness;
- contract adherence;
- visual reference score;
- technical pass rate;
- correction-loop convergence;
- number of unnecessary user questions;
- export correctness;
- resumability after interruption.
