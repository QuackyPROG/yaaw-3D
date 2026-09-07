# yaaw-3D agent operating contract

This repository implements a contract-first 3D production workflow.

## Non-negotiable invariants

1. Never begin modeling from the raw user request.
2. The Art Director owns ambiguity resolution and the production brief.
3. Ask intake questions in batches of exactly 10 whenever 10 unresolved material questions remain.
4. Every question must provide A/B/C choices, a recommendation, and a custom answer path.
5. Do not silently infer a material product detail when it affects geometry, style, topology, materials, animation, presentation, or delivery.
6. A locked production brief is the controlling input to downstream work.
7. The Planner may challenge the brief, but may not mutate it. Material ambiguity returns to the Art Director.
8. Builder output is provisional until Critic and Validator both pass it.
9. Critic feedback must become a concrete correction ticket; do not ask the Builder to "make it better."
10. Preserve job history. Never overwrite prior brief, plan, QA, or correction versions.
11. Technical validation and visual/artistic criticism are separate concerns.
12. Export only from a passing state and validate deliverables against the brief.

## Agent boundaries

- `art-director`: questions, contradictions, brief compilation, lock decision.
- `planner`: build strategy, milestones, dependencies, validation plan.
- `builder`: Blender-side modeling/lookdev/rigging/animation work through approved tools.
- `critic`: multi-view visual and craft criticism.
- `validator`: deterministic scene/mesh/delivery checks.
- `exporter`: final save/export/package validation.

Read the matching file in `agents/` before acting in a role and load only the specialist files in `skills/` required by the current phase.

## Job memory

Use `.yaaw3d/jobs/<job-id>/` as the durable trajectory. `state.json` is the current state; versioned files are immutable history.

## Completion

A job is complete only when:
- the brief is locked;
- the plan exists;
- Builder execution completed;
- Critic passes;
- Validator passes;
- requested exports exist and are validated.
