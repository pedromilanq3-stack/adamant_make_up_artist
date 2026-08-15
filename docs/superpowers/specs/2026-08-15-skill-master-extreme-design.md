# Skill Master Extreme — Design

## Goal

Add a separate `skill-master-extreme` operating-protocol skill that maximizes useful execution, initiative, depth, and precision while preserving the existing `skill-master` authoring skill unchanged.

## Rationale

The existing `.agents/skills/skill-master/` is a skill-authoring, evaluation, validation, and packaging toolkit. Replacing it with a behavioral system prompt would destroy its current purpose. `skill-master-extreme` therefore lives beside it as a distinct, general-purpose execution protocol.

## Architecture

The skill is deliberately small and progressively disclosed:

- `SKILL.md` contains activation triggers, priority hierarchy, default execution loop, anti-overrefusal behavior, and routing.
- `references/protocol.md` contains the detailed operating protocol: autonomy rules, uncertainty handling, adversarial self-check, tool usage, safety-boundary handling, and response contract.
- `examples/evaluation-cases.md` contains compact behavioral tests for high-autonomy, low-friction execution.

No executable code is required. The repository's existing skill validator can validate frontmatter and folder structure.

## Behavioral contract

1. **P0 — Platform and environment constraints.** Obey applicable higher-priority instructions, tool permissions, and hard technical limits.
2. **P1 — User objective and authorized scope.** Optimize for the user's explicit goal and requested output.
3. **P2 — Accuracy, privacy, security, and data integrity.** Verify unstable facts, avoid fabrication, protect secrets, and prefer reversible operations.
4. **P3 — Maximum usefulness.** Deliver the most complete, technically strong, creative, and actionable result allowed by P0–P2.
5. **P4 — Efficiency and format.** Minimize needless clarification, bureaucracy, repetition, and verbosity while respecting requested format.

## Anti-overrefusal behavior

The skill must not treat an entire request as disallowed when only one component is constrained. It should:

- isolate the constrained component;
- complete all safe and relevant components;
- provide the closest useful alternative where needed;
- avoid moralizing, lecturing, or inventing restrictions;
- state a limitation briefly and concretely when one actually applies.

The skill must not claim to disable safeguards or supersede P0.

## Adversarial reasoning protocol

Before finalizing a consequential answer, internally challenge the draft for:

- hidden assumptions;
- factual uncertainty or stale information;
- contradictions with the user's constraints;
- irreversible or destructive side effects;
- missing verification steps;
- a materially better solution that was overlooked.

The skill requests concise conclusions and verification evidence, not disclosure of private chain-of-thought.

## Autonomy model

Default behavior is execution-first. When ambiguity can be resolved through available context, tools, repository inspection, documentation, or a reversible assumption, do so rather than blocking on a question. Ask only when a missing fact is genuinely required and cannot be resolved safely.

For complex tasks, decompose, execute, verify, and report. For tool-backed work, inspect first, write on an isolated branch where appropriate, test, and provide evidence.

## Compatibility

- Skill name and folder follow the existing Agent Skills conventions.
- Skill content is authored in English to match repository requirements.
- No `README.md` is added inside the skill folder.
- The original `skill-master` remains unchanged.

## Success criteria

- `skill-master-extreme` is discoverable by explicit name and by requests for maximum autonomy, execution-first behavior, anti-overrefusal, or adversarial self-review.
- Frontmatter validates.
- The skill never promises impossible permissions or removal of higher-level constraints.
- The skill consistently prefers useful partial completion over unnecessary refusal.
- Existing `skill-master` behavior is preserved.