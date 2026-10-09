### Fresh new code project (build mode)

- **No reference system.** "Correct" is the spec: `docs/specs/<feature>.md` (from
  `_TEMPLATE.md`) with testable acceptance criteria. No spec → write one and get it
  confirmed before building anything non-trivial.
- **Architecture is decided once and recorded.** `context/projects/<project>/architecture.md` holds the
  layers, boundaries and data flow; any decision that is costly to reverse (new
  dependency, framework, data model, cross-cutting pattern) gets an ADR in `docs/adr/`.
  Follow accepted ADRs; propose a new ADR to change one — don't drift silently.
- **Conventions are written before code multiplies.** `context/projects/<project>/conventions.md`
  (naming, folder layout, error handling, testing, logging). New code follows it and
  `docs/design-principles.md`; YAGNI is the constraint most often broken here.
- **Tests come with the code.** Every acceptance criterion maps to a test or a recorded
  manual check; lint, typecheck, tests and build run green before review.
- Primary workflows: `workflows/scaffold-project.md` (repo bootstrap), `workflows/build.md`
  (each feature), `workflows/review-pr.md`.
