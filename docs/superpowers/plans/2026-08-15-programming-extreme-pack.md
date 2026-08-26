# Programming EXTREME Skill Pack Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Install the complete selected programming skill suite into `.agents/skills` for Codex and register every installed skill in `skills-lock.json`.

**Architecture:** Use the official `npx skills` CLI against authoritative GitHub sources. Install on an isolated branch, verify all expected `SKILL.md` entry points and lock entries, inspect the final diff, then merge only after successful validation.

**Tech Stack:** GitHub Actions, Node.js 22, Vercel Skills CLI, Agent Skills (`SKILL.md`).

## Global Constraints

- Preserve all existing skills and repository files.
- Install to the Codex project scope: `.agents/skills`.
- Use `--copy` so skill contents are committed and portable.
- Use authoritative upstream repositories only.
- Do not merge unless every expected skill has a `SKILL.md` and a `skills-lock.json` entry.
- Keep the installation workflow temporary; remove it before final merge.

---

### Task 1: Install Superpowers Complete Suite

**Files:**
- Create/update: `.agents/skills/<superpowers-skill>/...`
- Modify: `skills-lock.json`

**Interfaces:**
- Consumes: `obra/superpowers` official repository.
- Produces: 14 Superpowers skill directories registered for Codex.

- [ ] Install all skills from `https://github.com/obra/superpowers` with `--skill '*' -a codex --copy -y`.
- [ ] Verify the 14 expected entry points: `brainstorming`, `dispatching-parallel-agents`, `executing-plans`, `finishing-a-development-branch`, `receiving-code-review`, `requesting-code-review`, `subagent-driven-development`, `systematic-debugging`, `test-driven-development`, `using-git-worktrees`, `using-superpowers`, `verification-before-completion`, `writing-plans`, `writing-skills`.

### Task 2: Install Architecture, Modeling, Debugging, and Review Skills

**Files:**
- Create/update: `.agents/skills/improve-codebase-architecture/...`
- Create/update: `.agents/skills/codebase-design/...`
- Create/update: `.agents/skills/domain-modeling/...`
- Create/update: `.agents/skills/diagnosing-bugs/...`
- Create/update: `.agents/skills/code-review/...`
- Modify: `skills-lock.json`

**Interfaces:**
- Consumes: `mattpocock/skills` official repository.
- Produces: five engineering-specialist skills.

- [ ] Install the five named skills using the official Skills CLI.
- [ ] Verify each `SKILL.md` and lock entry.

### Task 3: Install Frontend, Browser, MCP, and PostgreSQL Skills

**Files:**
- Create/update: `.agents/skills/vercel-react-best-practices/...`
- Create/update: `.agents/skills/vercel-composition-patterns/...`
- Create/update: `.agents/skills/frontend-design/...`
- Create/update: `.agents/skills/webapp-testing/...`
- Create/update: `.agents/skills/mcp-builder/...`
- Create/update: `.agents/skills/agent-browser/...`
- Create/update: `.agents/skills/supabase-postgres-best-practices/...`
- Modify: `skills-lock.json`

**Interfaces:**
- Consumes: `vercel-labs/agent-skills`, `anthropics/skills`, `vercel-labs/agent-browser`, and `supabase/agent-skills`.
- Produces: seven specialized programming skills.

- [ ] Install the two Vercel React skills.
- [ ] Install the three Anthropic development skills.
- [ ] Install the agent-browser discovery skill.
- [ ] Install Supabase PostgreSQL best practices.
- [ ] Verify all seven `SKILL.md` files and lock entries.

### Task 4: Validate, Review, and Merge

**Files:**
- Verify: `.agents/skills/**/SKILL.md`
- Verify: `skills-lock.json`
- Remove: `.github/workflows/install-programming-extreme-pack.yml`

**Interfaces:**
- Consumes: all installed skill artifacts.
- Produces: a clean reviewable branch ready for merge.

- [ ] Count the expected 26 skill names and verify each exists.
- [ ] Parse `skills-lock.json` and verify all 26 names are registered.
- [ ] Confirm pre-existing skills remain present.
- [ ] Remove the temporary installer workflow after successful generation.
- [ ] Review `main...HEAD` for unrelated changes.
- [ ] Open a PR, verify mergeability/checks, and squash merge into `main`.