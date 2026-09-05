> Adapted from the supplied OpenAI Developers plugin on 2026-09-05. Read SKILL.md for environment limits and precedence. References here are files in this folder, not separately installed skills.

# Agents SDK

Use this skill to turn an idea or repo into a focused Agents SDK implementation.

## Before You Build

1. Use [openai-docs](openai-docs.md) to inspect current Agents SDK guidance.
2. If the work will call the OpenAI API, use [openai-platform-api-key](openai-platform-api-key.md) before live execution or verification of the API-backed path. Continue implementation and offline checks without a key.
3. Inspect the repo's existing language, package manager, entrypoints, and testing style before choosing a structure.

## Workflow

1. Define the agent contract:
   - goal
   - user input
   - expected output
   - tools
   - approval or escalation boundaries
2. Prefer the smallest runnable implementation first.
3. Use tools deliberately and keep side effects narrow.
4. Add evals when the user asks for reliability, comparison, or regression coverage.
5. Provide a local run command when implementation is requested. Report a concrete smoke result only if actually executed; otherwise specify the unrun check and reason.

## Guidance

- Prefer Python unless the repo or user already points to TypeScript.
- Start with one agent before introducing handoffs or orchestration.
- Keep prompts, tools, tests, and deployment artifacts clearly separated.
- Use [openai-docs](openai-docs.md) again when current SDK behavior or product guidance is central to the answer.
