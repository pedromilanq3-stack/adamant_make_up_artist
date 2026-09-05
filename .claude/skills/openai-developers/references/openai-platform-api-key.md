> Adapted from the supplied OpenAI Developers plugin on 2026-09-05. Read SKILL.md for environment limits and precedence. References here are files in this folder, not separately installed skills.

# OpenAI API Key Setup

Use this reference for manual key configuration and before authorized live OpenAI API calls. A missing key blocks only a live call; it does not block planning, implementation, documentation, examples, or offline tests.

## Determine the environment

1. Establish which environment will execute the request: the user's machine, the current sandbox, or a connected runtime. Do not confuse their credentials or filesystem access.
2. Respect the provider selected by the user. A generic request for AI does not authorize switching to OpenAI.
3. When filesystem access exists, inspect project conventions separately from secret-bearing files. Check only credential presence without exposing values. Presence is not proof that a key is valid, has quota, or can access a model.
4. Without access to the intended runtime, explain manual setup; do not claim to have inspected or configured it.

## Credential decision

- Reuse authorization already provided for this project's existing key. Do not ask the same question again.
- If a live request is requested but the credential choice remains unresolved, ask whether to use an existing key or create a new one manually. If the user explicitly wants a new key, go straight to manual setup.
- An existing credential alone does not authorize purchases, deployments, unrelated API calls, or access to other projects.
- Continue all authorized offline work while credential setup remains incomplete. Report only the live checks that were skipped.

## Manual setup

1. Direct the user to [Platform API keys](https://platform.openai.com/settings/organization/api-keys). This skill cannot mint or retrieve account keys automatically.
2. Ask the user to store the key privately as `OPENAI_API_KEY` in the environment where the app runs. Never ask them to paste it into the chat or upload a secret-bearing file.
3. Use an ignored local env file only when the application's loader actually supports it. Follow existing conventions: `.env`, `.env.local`, or a secret manager. A file named `.env.local` is not automatically loaded by every SDK or framework.
4. Keep keys in backend/server code, never browser JavaScript, public environment variables, committed source, or generated shareable artifacts. Example files may contain an empty `OPENAI_API_KEY=` only.
5. After manual configuration, verify presence without outputting the secret. If runtime access is unavailable, have the user run a presence-only check locally and report only present/absent.
6. Perform an authorized minimal live check only when it belongs to the task. Report presence, API authentication, and successful task execution as different levels of evidence.

## Safe inspection

- Use no-output or boolean checks of environment variables and known project env files. A matching variable name alone may still contain an empty or placeholder value.
- Never print, quote, mask-by-partial-display, summarize, or paste a key. Do not inspect secret files using `cat`, matching-line output, shell tracing, or verbose logs.
- Do not search unrelated home directories, accounts, projects, or credential stores.
- Do not change a custom `OPENAI_BASE_URL` silently or send a key to an unverified destination. Respect the approved project configuration and flag an unresolved endpoint before transmission.
- Write a secret only to a destination authorized by the user; resolve the destination if ambiguous. Never place credentials into a skill package.

For an actual failed request, continue with [openai-api-troubleshooting](openai-api-troubleshooting.md). For current setup guidance, use [openai-docs](openai-docs.md).
