> Adapted from the supplied OpenAI Developers plugin on 2026-09-05. Read SKILL.md for environment limits and precedence. References here are files in this folder, not separately installed skills.

# Build ChatGPT App

Use this skill for Apps SDK projects that combine an MCP server with a ChatGPT-facing tool or widget experience.

## Before You Build

1. Use [openai-docs](openai-docs.md) first for current Apps SDK guidance.
2. If the requested app or verification flow calls the OpenAI API, use [openai-platform-api-key](openai-platform-api-key.md) before live API execution or smoke tests. Continue implementation and offline checks without credentials. A tool-only MCP app may not need an OpenAI API key at all.
3. Inspect the target repo before choosing architecture.

## Workflow

1. Classify the app:
   - tool-only
   - widget-backed
   - submission-ready
2. Plan the tool surface before code:
   - tool names
   - input schemas
   - read/write behavior
   - annotations and expected outputs
3. Choose the smallest repo shape that fits the request.
4. Register the MCP server surface and widget resources deliberately.
5. Keep structured data, UI metadata, and side effects clear and reviewable.
6. Add local run instructions and basic verification steps when implementation is requested.

## Rules

- Prefer current OpenAI Apps SDK docs over stale examples.
- Keep tool annotations and widget metadata aligned with actual behavior.
- Treat CSP, domains, and submission-readiness as explicit design inputs when the app is meant for review or launch.
- Use [chatgpt-app-submission](chatgpt-app-submission.md) when the user needs submission-specific review preparation.
