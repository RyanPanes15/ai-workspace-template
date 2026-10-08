### Feature addition on an existing port (change mode)

- **The feature spec is the spec.** `docs/specs/<feature>.md` (or the change request)
  defines the new behavior; the divergence from the reference *is* the deliverable —
  never call it a regression. Ambiguity goes back to the requester.
- **Ported behavior must not break.** `context/parity-baseline.md` lists the behavior
  and checks that guard the existing port; consult the reference only for behavior
  the feature leaves untouched. A conflict with an earlier requested change is a
  question for the requester, not a defect.
- **Fit the existing port.** Reuse its components, presets and patterns; no new visual
  vocabulary; regression-test every consumer of a shared component you touch.
- **Comments:** ported code keeps its original comments; new feature code follows the
  short-comment rule.
- A bug found in delivered feature work is handled in defect mode (`workflows/fix.md`).
- Primary workflows: `workflows/change-request.md` (analyze → implement), `workflows/build.md`
  for net-new modules with no reference counterpart, `workflows/review-pr.md`.
