# Safety and scope

## Allowed project shape

Build a deliberately isolated teaching application with generated users, posts,
sessions, reset tokens, and authorization resources. Demonstrations may expose
weak behavior inside that application when the weakness is paired with a fix,
tests, and a detection event.

Appropriate scenarios include:

- predictable lab-only session identifiers versus random rotated identifiers;
- reusable synthetic recovery tokens versus expiring single-use tokens;
- missing ownership checks on generated records versus server-side authorization;
- absent rate limiting versus a deterministic local throttle;
- incomplete audit logs versus structured local security events.

## Disallowed project shape

Do not build functionality that targets a real username, account, organization,
website, API, mobile application, or authentication provider. Do not ingest real
credentials or session artifacts. Do not add phishing, credential collection,
account discovery, session replay against external services, password spraying,
2FA interception, recovery-flow abuse, or instructions for bypassing a platform.

If a user supplies a real-looking handle, derive a clearly synthetic lab handle
such as `@name_demo`, explain the substitution in the UI, and keep every record
inside local fixtures.

## Evidence standard

For each scenario, record:

1. scenario identifier and synthetic actor;
2. controlled action performed;
3. vulnerable outcome;
4. local detection event and timestamp;
5. secure outcome after mitigation;
6. automated assertion proving the expected difference.

Use generated evidence suitable for screenshots and an academic appendix. Never
present a real person's data, real platform screen, or live account as evidence.

