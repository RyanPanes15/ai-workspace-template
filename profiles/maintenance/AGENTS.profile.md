### Maintenance project (defect mode)

- **Released behavior is the baseline.** A report is a claim to verify, not a spec:
  confirm its premise, reproduce it (pre-fix control), then fix the root cause.
- **Evidence names its environment.** Keep `context/projects/<project>/environment.md` current (which DB,
  log source, build and account each environment uses) and `context/projects/<project>/test-records.md`
  for known repro records.
- **Requested changes are not regressions.** Check `context/projects/<project>/spec-changes.json` before
  calling a behavior difference a defect.
- **One item per PR; sweep for the same defect elsewhere; reviewer round before push.**
- Primary workflows: `workflows/analyze.md` → `workflows/fix.md`, `workflows/log-triage.md`,
  `workflows/db-query.md`, `workflows/stakeholder-reply.md`, `workflows/area-loop.md` for
  clusters.
