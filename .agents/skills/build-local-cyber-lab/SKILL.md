---
name: build-local-cyber-lab
description: "Build or extend an ethical localhost web-security teaching lab with synthetic profiles, vulnerability demonstrations, mitigations, monitoring, tests, Docker, and academic documentation. Use for cyber lab, local CTF, authentication lab, session security, password reset, or access-control coursework."
---

# Build Local Cyber Lab

Create an educational web-security lab that is convincing enough for a live
academic demonstration while remaining isolated from real accounts and services.

## Workflow

1. Inspect the target repository and its applicable instructions.
2. Define the synthetic profile, learning objectives, and three or more scenarios.
3. Read [safety-and-scope.md](references/safety-and-scope.md) and enforce every
   boundary before writing code.
4. Choose an implementation path:
   - Extend the repository's existing stack when it already has a runnable app.
   - Copy the starter from `assets/cyber_lab/` and `assets/Dockerfile.lab` when a
     dependency-free Python baseline is appropriate.
5. Implement each scenario with four visible parts:
   - vulnerable behavior contained within the lab;
   - deterministic demonstration action;
   - detection or audit event;
   - corrected behavior and concise mitigation explanation.
6. Label every fake identity and simulated event clearly in the interface.
7. Bind directly to `127.0.0.1`. In containers, bind internally to `0.0.0.0`
   only when the documented run command publishes to `127.0.0.1` on the host.
8. Add automated tests for scenario allowlisting, mitigations, local scope,
   unknown-scenario rejection, and relevant HTTP responses.
9. Run the app and test one complete interaction. Capture a screenshot when the
   UI changes and the environment supports a browser.
10. Document direct and Docker execution, ethical limitations, test commands,
    and the presentation flow.

## Required guardrails

- Use a conspicuously synthetic handle such as `@student_demo`; add `_demo` or
  `_lab` when adapting a user-provided name.
- Never request or store real passwords, cookies, tokens, recovery codes, 2FA
  codes, personal exports, or private content.
- Never connect to, scrape, imitate the login endpoint of, or automate actions
  against a real social platform.
- Do not claim that descriptive text alone is a working vulnerability. Make the
  local scenario testable, but constrain all state, identities, and resources to
  fixtures created for the lab.
- Reject scenario names and resource identifiers outside an explicit allowlist.
- Keep attacker and victim roles synthetic and provide resettable lab state.
- Stop and replace the target with a synthetic equivalent if a request shifts
  toward a real account or external service.

## Starter asset

The `assets/cyber_lab/` starter provides a standard-library HTTP server, static
interface, three allowlisted scenarios, simulated detection evidence, and secure
response headers. Copy it rather than editing the installed skill:

```bash
cp -R <skill-directory>/assets/cyber_lab ./cyber_lab
cp <skill-directory>/assets/Dockerfile.lab ./Dockerfile.lab
python -m cyber_lab.app
```

Treat the starter as a baseline. Add persistent state only when the requested
exercise needs it, and keep fixtures resettable and non-sensitive.

## Completion checklist

- Confirm all names and data are synthetic.
- Confirm normal execution makes no external network request.
- Confirm every vulnerability has a mitigation and detection signal.
- Confirm tests cover both accepted and rejected actions.
- Confirm local-only run instructions are accurate.
- Report changed files, exact validation commands, and any environment limits.

