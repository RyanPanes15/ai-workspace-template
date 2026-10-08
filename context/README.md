# context/

Project-specific knowledge the agent reads on demand (AGENTS.md holds only rules).

- `repos/<name>.md` — one per registered repo; generated once by setup, then yours.
- `environment.md` — how to run the stack, which DB/log environment is which.
- `test-records.md` — known-good repro records (keys, instance, state, date verified).
- `domain-glossary.md` — domain terms, status enums, IDs; keep original-language terms.
- `spec-changes.json` (optional) — requested changes per area with a code-verification
  verdict, so a difference from the reference is not mistaken for a regression.

Keep entries terse; generalize rules into AGENTS.md / docs when they recur.
