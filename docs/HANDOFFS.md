# Handoff contracts

## Art Director → Planner

Must include:

- locked brief version;
- exact requirements;
- unresolved = `[]`;
- contradictions = `[]`;
- acceptance criteria.

Planner rejects unlocked briefs. If user intent changes after lock, the job must use `revise-brief`; direct answer mutation is blocked.

## Planner → Builder

A plan must identify:

- milestone id;
- objective;
- allowed tool domain;
- input objects;
- expected output;
- required review captures;
- validation checks;
- save point.

A non-empty `milestones` list is required before `begin-build`.

## Builder → Critic

Provide artifact/milestone id and evidence views. The Builder does not self-certify visual quality.

## Critic → Builder

Failures become correction tickets with artifact id, evidence, bounded changes, and re-test criteria.

## Builder → Validator

Provide exact scene state/version. Validator reports measurements, not aesthetic commentary.

## Validator → Exporter

Requires visual pass + technical pass for the accepted iteration.

## Exporter → Complete

Requires requested deliverables plus export validation evidence. A passed export report must include at least one file path.
