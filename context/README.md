# context/

Project-specific knowledge the agent reads on demand (AGENTS.md holds only rules).

- `repos/<name>.md` — one per registered repo; generated once by setup, then yours.
- `projects/<project>/` — one per project; setup scaffolds the files its types need:
  - `architecture.md`, `conventions.md` — greenfield: layers, boundaries, naming, layout.
  - `port-map.csv`, `port-conventions.md` — port: area tracking, concept mapping.
  - `parity-baseline.md` — feature: ported behavior that must not break.
  - `environment.md` — how to run the stack, which DB/log environment is which.
  - `test-records.md` — known-good repro records (keys, instance, state, date verified).
  - `domain-glossary.md` — domain terms, status enums, IDs; keep original-language terms.
  - `spec-changes.json` (optional) — requested changes per area with a code-verification
    verdict, so a difference from the reference is not mistaken for a regression.

Keep entries terse; generalize rules into AGENTS.md / docs when they recur.
