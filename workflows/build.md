# Workflow: Build a feature (spec → code → evidence)

**Mode:** build (greenfield) or change (net-new module on an existing port).
**Tier:** deep @ high. **Input:** a feature name or spec path.
Invoking this workflow is consent for its documented steps; push and PR still need an
explicit "yes".

1. **Plan.** Create `_work/runs/<feature>/TASKS.md` (AGENTS.md §5). Read
   `mistakes/INDEX.md` and open the matching files.
2. **Spec.** Find or write `docs/specs/<feature>.md` from `docs/specs/_TEMPLATE.md`:
   problem, testable acceptance criteria, non-goals, design notes, open questions.
   Unresolved questions that change what ships → ask before building. Record answers in
   the spec.
3. **Context.** Read `context/architecture.md`, `context/conventions.md`, accepted ADRs
   (`docs/adr/`), and the repo context files. On an existing port, also
   `context/parity-baseline.md`. Find existing components to reuse
   (`area_index.py`, `cs.py find` / `cs.py refs`) before creating new ones.
4. **Design note** (in the spec's *Design notes*): which layers change, new types /
   endpoints / tables, what is reused. Apply `docs/design-principles.md`. A decision that
   is costly to reverse (new dependency, framework, data model, cross-cutting pattern) →
   draft an ADR (`docs/adr/NNNN-*.md`, status *proposed*) and get it accepted first.
5. **Tests first where the repo supports it.** One test (or recorded manual check) per
   acceptance criterion; add edge cases: empty / max length (bytes where it matters) /
   invalid / unauthorized / concurrent.
6. **Implement in small commits** — one concern per commit; restructuring needed by the
   feature goes in its own no-behavior-change commit first. Validation is authoritative
   on the server; the client mirrors it for UX. Follow the comment rules
   (`docs/design-principles.md` § Comments).
7. **Cross-layer check.** For any new value crossing a boundary, dispatch
   `fix-verifier` (client value ⇄ API schema ⇄ DB constraint).
8. **Verify.** Lint (`modules/lint-gate`), typecheck, tests and production build actually
   run and pass on the changed files; run the app and capture evidence for each
   acceptance criterion into the spec's *Evidence* table (observed values, not "works").
   On an existing port, run the parity-baseline checks for every shared component touched.
9. **Simplicity pass**, then a **self-review** with `workflows/review-pr.md` against your
   own diff (merge-blocking problems only). Fix what it finds.
10. **Report** — what I need from you → summary → acceptance-criteria evidence → files →
    follow-ups. **PR** per `docs/git-workflow.md` on confirmation. Close `TASKS.md`.
11. **Record** any mistake caught along the way in `mistakes/` (AGENTS.md §10).
