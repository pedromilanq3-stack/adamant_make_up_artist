# Skill Master Extreme Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a separate high-autonomy execution protocol skill named `skill-master-extreme` without modifying the existing `skill-master` authoring skill.

**Architecture:** Keep the top-level `SKILL.md` concise and activation-focused. Put the full operating protocol in `references/protocol.md` and behavioral acceptance cases in `examples/evaluation-cases.md` so the skill uses progressive disclosure and remains maintainable.

**Tech Stack:** Markdown, YAML frontmatter, existing Python skill validator in `.agents/skills/skill-master/scripts/quick_validate_skill.py`.

## Global Constraints

- Author all skill content in English.
- Keep the existing `.agents/skills/skill-master/` unchanged.
- Do not add `README.md` inside the new skill.
- Do not claim the skill can override platform instructions, permissions, or hard technical limits.
- Prefer execution-first behavior and useful partial completion over unnecessary clarification or broad refusal.
- Do not expose private chain-of-thought; provide concise conclusions and verification evidence instead.

---

### Task 1: Add the Skill Entry Point

**Files:**
- Create: `.agents/skills/skill-master-extreme/SKILL.md`

**Interfaces:**
- Consumes: Agent Skills frontmatter conventions from the existing `skill-master`.
- Produces: Discovery metadata and the primary operating instructions for `skill-master-extreme`.

- [ ] **Step 1: Create valid YAML frontmatter**

Use `name: skill-master-extreme`, a concise trigger-rich description, and metadata version `1.0.0` with release date `2026-08-15`.

- [ ] **Step 2: Define the priority hierarchy**

Encode P0 through P4 exactly as specified in the design.

- [ ] **Step 3: Define the execution loop and anti-overrefusal rules**

Require context-first execution, reversible assumptions, tool use where useful, partial completion when only part of a request is constrained, and concise limitation statements.

- [ ] **Step 4: Route detailed behavior to the protocol reference**

Link `references/protocol.md` for the full autonomy, uncertainty, adversarial self-check, tool, and response rules.

- [ ] **Step 5: Commit the entry point**

Commit message: `feat: add skill-master-extreme entry point`.

### Task 2: Add the Detailed Operating Protocol

**Files:**
- Create: `.agents/skills/skill-master-extreme/references/protocol.md`

**Interfaces:**
- Consumes: Priority hierarchy and execution contract from `SKILL.md`.
- Produces: Detailed behavior rules used after skill activation.

- [ ] **Step 1: Add maximum-autonomy defaults**

Specify execution-first behavior, context/tool resolution before questions, decomposition for complex tasks, and reversible-action preference.

- [ ] **Step 2: Add uncertainty and verification rules**

Require explicit uncertainty, verification of unstable facts, source-of-truth preference, and no fabrication.

- [ ] **Step 3: Add adversarial self-review**

Require an internal challenge pass for assumptions, stale facts, user-constraint conflicts, destructive side effects, missing verification, and overlooked better solutions.

- [ ] **Step 4: Add boundary handling**

Require narrow handling of constrained components, safe completion of the remainder, nearest useful alternatives, and no invented restrictions or moralizing.

- [ ] **Step 5: Commit the protocol**

Commit message: `feat: add extreme execution protocol`.

### Task 3: Add Behavioral Acceptance Cases

**Files:**
- Create: `.agents/skills/skill-master-extreme/examples/evaluation-cases.md`

**Interfaces:**
- Consumes: `SKILL.md` and `references/protocol.md` behavior requirements.
- Produces: Human-readable regression cases for future skill evaluation.

- [ ] **Step 1: Add execution-first cases**

Cover missing-but-resolvable context, multi-step repository work, and reversible assumptions.

- [ ] **Step 2: Add anti-overrefusal cases**

Cover mixed requests where one component is constrained but the remainder is useful and allowed.

- [ ] **Step 3: Add verification cases**

Cover current information, tool-backed claims, and post-change validation evidence.

- [ ] **Step 4: Add private-reasoning case**

Require concise rationale and evidence without chain-of-thought disclosure.

- [ ] **Step 5: Commit acceptance cases**

Commit message: `test: add skill-master-extreme behavior cases`.

### Task 4: Validate and Review

**Files:**
- Verify: `.agents/skills/skill-master-extreme/SKILL.md`
- Verify: `.agents/skills/skill-master-extreme/references/protocol.md`
- Verify: `.agents/skills/skill-master-extreme/examples/evaluation-cases.md`

**Interfaces:**
- Consumes: New skill files.
- Produces: Validation evidence and review-ready branch.

- [ ] **Step 1: Run structural validation**

Run:

```bash
python .agents/skills/skill-master/scripts/quick_validate_skill.py .agents/skills/skill-master-extreme
```

Expected: validation succeeds with exit code 0.

- [ ] **Step 2: Search for prohibited placeholders**

Run:

```bash
grep -RniE 'TBD|TODO|implement later|fill in' .agents/skills/skill-master-extreme
```

Expected: no matches.

- [ ] **Step 3: Confirm existing skill is untouched**

Run:

```bash
git diff main...HEAD -- .agents/skills/skill-master/SKILL.md
```

Expected: no diff.

- [ ] **Step 4: Review branch diff**

Check that the new skill is separate, concise, triggerable, and contains no claim of bypassing higher-level constraints.

- [ ] **Step 5: Prepare review handoff**

Create a pull request summarizing architecture, behavior changes, and validation results.