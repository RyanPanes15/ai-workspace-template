### Port migration (port mode)

- **Parity is the spec.** The reference system's observable behavior defines correct,
  unless `context/spec-changes.json` records a requested change. A claim about the
  reference needs the reference artifact (and the deployed build when they disagree).
- **Inventory before code.** Every area is ported through `workflows/port-feature.md`:
  logic inventory → gap analysis → layer split → generate → completeness verifier.
  Track each area in `context/port-map.csv`; `python modules/port-status/port_status.py`
  reports progress and checks the map.
- **Re-derive, don't transliterate.** Write the target stack's idiom using
  `context/port-conventions.md` (concept mapping, naming, null/encoding rules). Never
  copy reference code; never adopt its architecture wholesale.
- **Carry the reference's comments over as they are** onto the equivalent new code; the
  short-comment rule applies only to code the reference does not have.
- **Integrity rules live on the server**, UX rules on the client; many need both.
- Primary workflows: `workflows/port-feature.md`, then `workflows/analyze.md` /
  `workflows/fix.md` for port regressions, `workflows/review-pr.md`.
