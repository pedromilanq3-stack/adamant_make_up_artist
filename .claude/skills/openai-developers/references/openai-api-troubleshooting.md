> Adapted from the supplied OpenAI Developers plugin on 2026-09-05. Read SKILL.md for environment limits and precedence. References here are files in this folder, not separately installed skills.

# OpenAI API Troubleshooting

Use this for runtime OpenAI API failures after a request has already been made. Keep key setup in [openai-platform-api-key](openai-platform-api-key.md) and current guidance in [openai-docs](openai-docs.md).

## Routing

1. Sandboxed or blocked outbound network access
   - Treat DNS errors, connection timeouts, connection resets, or inability to reach `api.openai.com` before any API response as transport problems first.
   - If the failure came from a sandboxed or restricted run, identify the transport restriction and use an already permitted execution path; if this environment cannot reach the API, provide a local command for the user to run in their own authorized runtime. Do not bypass network controls; only classify API-side auth, quota, rate-limit, or model access after a concrete OpenAI response exists.

2. Authentication or missing-key errors
   - Route `401`, `invalid_api_key`, missing `OPENAI_API_KEY`, or malformed-key cases to authentication.
   - If a key must be created or configured, explicitly hand off to [openai-platform-api-key](openai-platform-api-key.md); do not stop at generic "create a fresh key" advice.

3. Quota or credit exhaustion
   - Treat `insufficient_quota`, "current quota", "billing quota", "run out of credits", or "no balance left" as billing/quota exhaustion, not ordinary throttling.
   - For exhausted credits, prompt the user to add credits and include [Add API credits](https://platform.openai.com/settings/organization/billing/overview). Do not purchase credits or change billing settings.
   - Link usage caps to `https://platform.openai.com/settings/organization/limits`.
   - If ambiguous, say it may be credits or a spend limit and consult [openai-docs](openai-docs.md); when useful, note that ChatGPT subscriptions and API billing are separate.

4. Rate limits
   - Route `rate_limit_exceeded`, requests-per-minute, tokens-per-minute, or retry-after guidance without quota language to throttling.
   - Recommend pacing, batching, exponential backoff, or lower concurrency; do not suggest buying credits unless the error also indicates quota exhaustion.

5. Model, project, or organization access
   - Treat permission failures, `403`, `model_not_found` (which may also accompany `404`), and org/project mismatch as model/project/access issues. Check the concrete code and body: the identifier may be invalid or unavailable, rather than every case being an authorization failure.
   - Check the model, project, organization, and key scope before guessing.

## Rules

- Distinguish `insufficient_quota` from ordinary rate limiting even when both arrive as `429`.
- Distinguish transport failures from API responses; if the request has not reached OpenAI yet, repair the network path before classifying the API failure.
- Prefer the concrete API error code and message over generic heuristics.
- Keep user-facing answers short: likely class, reason, next action.
- Do not rotate or create keys here.
- Use [openai-docs](openai-docs.md) when remediation depends on current guidance, links, limits behavior, or wording that may drift.
