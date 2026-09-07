# Handoff contracts

## Art Director → Planner

Must include:
- locked brief version;
- exact requirements;
- unresolved = `[]`;
- contradictions = `[]`;
- acceptance criteria.

Planner rejects unlocked briefs.

## Planner → Builder

A plan should identify:
- milestone id;
- objective;
- allowed tool domain;
- input objects;
- expected output;
- required review captures;
- validation checks;
- save point.

## Builder → Critic

Provide artifact/milestone id and evidence views. The Builder does not self-certify visual quality.

## Critic → Builder

Failures become correction tickets with bounded changes and re-test criteria.

## Builder → Validator

Provide exact scene state/version. Validator reports measurements, not aesthetic commentary.

## Validator → Exporter

Requires visual pass + technical pass for the same accepted iteration.

## Exporter → Complete

Requires requested deliverables plus export validation evidence.
