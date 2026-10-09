# Workflow: Change requests — analyze, then implement

**Mode:** change mode (AGENTS.md §2): the request text is the spec; the reference
only defines what must not break. **Tier:** deep @ high.

Read `mistakes/INDEX.md` first and open matching files (AGENTS.md §10).

## Part 1 — Analyze (`/analyze-change CR-<n>[@<area>]`) — read-only
1. Load the request (tracker/catalog) and any decisions recorded since (meeting notes,
   threads, reviewer findings, attached layout files).
2. **Reconstruct the requirement** in one paragraph + a numbered list of concrete,
   testable changes; start from `_work/runs/<task>/BRIEF.md` when one exists. Mark every ambiguity as a question for the requester.
3. Classify: **layout/UI-only** vs **functional** (functional = estimate and approval
   before any code).
4. Read the current implementation of every touched area. When the request copies
   something another screen already has, take it from there as slices:
   `cs.py field <field> --scope <that screen> --show` (implementation to mirror) and
   `cs.py refs <component>` (other consumers to regression-test).
5. Read the reference only for (a) domain semantics the request assumes and (b) the
   untouched behavior on the same screen — the regression baseline.
6. Impact: shared components touched, data changes, API/DB changes, blast radius.
7. **In-flight collision check:** open branches/PRs touching the same files
   (`git diff origin/<a>...origin/<b> -- <files>` across integration branches).
8. Sweep: where else the same change pattern belongs (report-only).
9. Write the trail: append the Part 1 output as a dated section to
   `reports/<CR-id>-analysis.md` — Part 2 starts cold from it in a fresh session
   (`/clear`, then `/implement-change`), never from this transcript.
9. Draft **acceptance criteria** (Given/When/Then or checklist), one per change.
10. Estimate + risk; recommendation: implement / clarify / out of scope.
11. A conflict with an earlier requested-and-shipped change is a **requester-side
    contradiction** → a question, not a defect.

## Part 2 — Implement (`/implement-change CR-<n>@<area>`)
1. Load the Part 1 output from `reports/<CR-id>-analysis.md` (re-verify every anchor);
   refuse to proceed on a functional change without recorded
   approval.
2. **Ask the target integration branch every time** (bases can diverge per team);
   record any cherry-pick plan.
3. Apply the team's coding/style guide for changes of this kind (`context/` or docs repo).
   **No new visual vocabulary:** use only the components, presets, colors, spacing and
   typography the codebase or design system already defines. Anything in the request
   with no existing equivalent goes back as a question, not an invented style. For
   vague asks ("cleaner", "modern"), ask which elements change; never fall back on
   generic defaults (off-white backgrounds, pill buttons, numbered section labels,
   monospace labels, italic accent words).
3b. New code follows `docs/design-principles.md`; comments only where needed, one short
   line on what the code does.
4. Implement; regression-test the **shared atoms** touched (every consumer); the
   untouched behavior must match the baseline from Part 1 step 5.
5. Map each acceptance criterion → evidence (screenshot/value/test) in the report.
6. PR per `docs/git-workflow.md`, change-request naming from the workspace map.
7. Hand-off checklist the developer performs (tracker update, team notification) —
   agents draft, never post.
