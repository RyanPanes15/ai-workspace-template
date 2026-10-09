# Workflow: Fix a work item end-to-end

**Mode:** defect mode. **Tier:** deep @ high (escalate a tier manually only for
returned-for-rework, cross-repo + cross-layer, or an already-refuted hypothesis).
**Input:** one item ID. One item per invocation; bundling needs explicit consent.
Invoking this workflow is consent for its documented investigation, sweep, and
regression steps. **Tests, push and PR each still need an explicit "yes".**

---

### Step 1 — Load context
Create `_work/runs/<ID>/TASKS.md` listing every step below that applies (AGENTS.md
§5); tick items as you go. Read `mistakes/INDEX.md` and open matching files (AGENTS.md §10).
Load the item record and the prior analysis trail from **`reports/<ID>-analysis.md`**
— the default is a cold start in a fresh session, with the trail as the handoff; the
transcript of an earlier analysis in this session is a convenience, not the source.
If no trail exists, run `workflows/analyze.md` first (it writes one). Every anchor in
the trail is re-verified in Step 5.0 before it is used.

### Step 2 — Scope
Which repos? Routing default: UI → frontend repo; data/logic → backend repo; both →
backend first. Check repo roles: **flag-only** repo involved → describe the needed
change and stop for that part; prefer a fix path in a modifiable repo. Cross-repo →
confirm with the developer (A: both now / B: one now, defer other / C: stop).

### Step 3 — Pre-flight
`git -C <repo> branch --show-current` and `status -s`. Repeat before every edit batch.

### Step 4 — Runtime-evidence gate
Runtime-state symptom (enable/disable, blank-on-load, stale value, toggle, async
ordering, latency, empty dropdown): carried-forward confidence **HIGH** → proceed;
**MEDIUM** → suggest a self-test, developer decides (note "fixed on a static medium
hypothesis" if declined); **LOW** → run the self-test first. Never commit a fix on an
unverified runtime hypothesis — those ship and get reverted.

### Step 5 — Implement
0. **Scaffold before editing** (multi-file / multi-hunk / prior-session analysis):
   read-only subagent per target file re-verifies every cited anchor against the
   *current* tree and returns verbatim edit specs (unique anchor + replacement);
   prompt per `.claude/model-routing.md` §Subagent brief.
   Same-file edits are applied sequentially in one tree — never parallel worktrees.
1. Ground the change in the behavior contract. Conflict between reference and
   spec/report → stop and surface.
2. Tests where the repo's pattern supports it; otherwise state "manual verification
   only" — never fabricate a stub.
3. **Comments** (`docs/design-principles.md` § Comments): only where the code is not
   self-explanatory, one short line on what it does — never what it is for, why, or
   an item ID. The PR and trail are the explanation layer. When the fix restores
   behavior ported from the reference, the reference's own comments for that code are
   carried over as they are.
3a. **Root cause, not symptom.** A workaround that only hides the symptom needs a
   *temporary* label, developer approval and a follow-up item.
3b. **Structural change first, separately.** If the fix needs code restructured, make
   that a no-behavior-change commit before the fix (state how you showed behavior is
   identical); beyond the files the fix already touches, ask first.
4. **Ripple defects** found while editing → `[A] bundle (only ≤2-line trivial) / [B]
   defer (draft new items) / [C] stop`. Default: surface and wait.
5. **Framework-setter check** (UI state libraries): direct mutation of form/store
   state without the framework setter → stale reads; surface as ripple defects.
6. **End-to-end flow** — success path produces the expected state; at least one error
   path shows a *visible* error (silent error drops are a classic port gap). If not
   runnable in-session, say so explicitly. A clean typecheck/lint is not "done".
7. **Spec ambiguity** → open the one authoritative spec file for this area (by known
   path, never glob). Silent spec → note for reviewer + recommend a stakeholder
   question. Never edit the spec.
8. **No lint, push, or PR yet.**

### Step 6 — Regression analysis
Blast radius, callers, sibling paths, data-shape risk, cross-repo risk, QA coverage.
Plus, explicitly:
- **Revived code:** list every branch the fix makes reachable (read the *pre-fix*
  file); audit each one's value domains (string vs number compares, NaN, sentinels,
  empty strings, unreachable notifications, state captured before a reset). Re-read
  the reference for value domains, not only control flow. "Fix revives no dead code"
  must be stated if true.
- **Suppress-style fixes:** (1) writes that no longer run; (2) **invariant partners**
  of the writes that still run (list + index + detail must stay consistent).
- Does the fix's own shape reproduce the hazard (e.g. a falsy-default opt-out flag on a
  multi-caller function)?
- **Invert every reviewer finding** ("fires when it shouldn't" → "where does it fail to
  fire when it should?") — a finding defines a class, not a checklist item.
- Recent changes to the same files (last 30 days) — confirm no conflict.
- Callers of every changed module/area (`area_index.py --callers <area>`; for a changed
  function, `cs.py refs <name>` lists each calling function without the bodies) — each
  is a regression candidate.

### Step 7 — Horizontal sweep (横展開 / yokoten)
1. Write the **pattern signature** and the defect class in one sentence with **zero
   identifiers**. If your search key is an identifier fragment or naming glob, you
   are name-scanning — re-key on roles.
2. Scope: modifiable repos at medium depth (structural grep); reference repos only
   if Tier 2 fired; widen with historical and same-author areas (internal tag only).
3. Run the same detector on a **known-good control**; a hit there is noise floor.
4. Open every candidate before listing or dismissing it.
5. Tier each site: **A** exact (same fix verbatim) · **B** related (per-site audit) ·
   **C** architectural (own analysis). Action: A ≤8 files → same PR; A >8 → split;
   B → separate PRs; C → new items. Developer decides.

### Step 7.5 — Simplicity pass (non-trivial changes)
Ask once: knowing what you know now, is there a simpler or cleaner change at the right
layer (`docs/design-principles.md` § Simplicity pass)? If yes, redo it now — before the
reviewer round, not after. Skip for obvious one-line fixes.

### Step 8 — Structured report
**What I need from you** (decisions, approvals, manual checks — or "nothing") first, then summary · root cause (file:line) · fix · regression · sweep · reviewer round (after
9.5) · commit/PR drafts · next steps. May dispatch `report-formatter` (light).

### Step 9 — Offer tests
Offer; run only on "yes". Run them through `test-runner` (light) using the **Quiet
commands** in `context/repos/<name>.md`: only failures and the executed counts enter
this context, never the full log. Confirm the tool actually ran (`ran=` > 0, correct
files, correct branch; for lint, `modules/lint-gate` refuses the vacuous cases) — a
clean exit with nothing executed is not a pass.

### Step 9.5 — Reviewer round (mandatory before push)
**Size it to the change.** Copy-only changes (labels, message text, captions, headers,
placeholders — no logic, state, style binding or request payload) get a reduced round:
the claim (1), one before/after screenshot of the same screen (with the reference beside
it if it defines the wording), PR-text check (8), and a grep for other places rendering
the same string. Anything touching a condition, handler, state, visibility or payload
gets the full round. When in doubt, it is not copy-only.

**The full round runs in `fix-reviewer` (deep subagent), not inline**, so its probes,
screenshots and re-greps never ride along in this session. The reduced copy-only round
stays inline. Before dispatch, the main agent:
- restates the claim as a falsifiable sentence in the reporter's terms: "On <screen>,
  doing <action> now produces <expected> instead of <reported>" (can't → back to Step 5);
- **hands over the pre-fix control**: the evidence already captured that reproduces the
  symptom (Step 4 runtime gate, the analyze repro, or a run made before editing). A
  subagent in the shared working tree cannot stash the fix to re-create it. If none
  exists, create a read-only pre-fix checkout under `_work/worktrees/<ID>-prefix/`
  (`git worktree add --detach`) and pass its path;
- passes: the claim, item record + trail path, changed files (`git diff --name-only`),
  the evidence dir `_work/evidence/<ID>/`, the repo context files, the quiet commands,
  `docs/verification-guide.md`, and the attack list below.

The reviewer attacks the *claim*, not the diff:
1. The falsifiable restatement holds (or is corrected).
2. **Paired A/B, pre-fix control first**, same record / instance / input path. The
   control must reproduce the symptom, or the post-fix pass is vacuous.
3. **Assert every trial executed** (request in log, row written, handler entered).
4. **Drive every input path** that can commit the value (type, paste, picker,
   dropdown, IME, blur, Enter) and confirm the field's *state* arms the code path.
5. Name DB instance + log environment per observation.
6. Re-run the sweep from the **defect's defining relation**, with a control.
7. Audit revived paths and removed writes (Step 6) once more.
8. Verify every mechanism sentence in the PR body / commit message against a line
   read in the review; re-verify every file:line.
9. Write the evidence artifact (below). A round reporting "no findings" must name
   what it tried to break, with proof each attack executed.

It returns `ACCEPTED | REJECTED | NEEDS DEVELOPER`, the attacks table, findings with a
proposed disposition, and the artifact path. Then the main agent:
- **REJECTED blocks the push.** Fix, then re-dispatch; do not argue with the report.
- **NEEDS DEVELOPER** items (a manual check, an environment the reviewer could not
  reach) go to the top of *what I need from you*.
- Dispatches `fix-verifier` for cross-layer changes after the reviewer returns;
  **REJECTED blocks the push**. Every finding → fixed now / new task / reviewer note.

Evidence artifact: `_work/evidence/<ID>/FIX-VERIFICATION-<YYYYMMDD>.md` +
`<ID>-fix-verified-<YYYYMMDD>-<slug>.png` per distinct expected result, containing:
header (screen, env, DB instance, tenant) · exact record keys · fix in 2–3 sentences ·
expected-vs-observed table (Expected = reporter's wording; Observed = the actual
value, never "works") · the pre-fix control and **which check discriminates** ·
captioned screenshots (value legible at full resolution) · probe warnings · cross-refs.
Prefer the repo's scripted browser harness over click-by-click tooling
(`docs/verification-guide.md` §Scripted driver).

### Step 10 — Push and PR (on explicit confirmation only)
Follow `docs/git-workflow.md` 10.1–10.10 in order: working-tree pre-flight → auth →
branch → PR-wide lint auto-fix → stage-by-name commits per item (≤72-char header,
file-based message) → merge-pull integration branch (conflict → stop) → diff-based
lint gate (feature branch as argument) → push → `gh pr create --base <integration>
--body-file` → echo URL → optional notify → return to integration branch + restore
stash → delete temp auth helpers. Cross-repo: per repo, in merge order.

### Step 11 — Record (best-effort)
Update tracking/metrics if the module is enabled; append a dated section to
`reports/<ID>-analysis.md`; record the outcome (`usage_tracker.py --outcome <ID> …`,
see `workflows/export.md`); close `TASKS.md` with its *Results* section. End with
the handoff line for the next task (`/clear` first).
If the reviewer round, the developer, or a test caught something you got wrong in this
item, update or add the matching `mistakes/` file now (AGENTS.md §10).

## Hard rules
- Runtime gate, reviewer round, and confirmation gates are not skippable.
- Never modify read-only / flag-only repos. Never amend / force-push.
- No silent scope expansion; single item per PR by default.
- Every reference citation pairs with a recommendation.
- Author/implementer data stays internal.
- The tool surface is permissive because this is the only mutating workflow —
  discipline lives in the procedure, not in missing permissions.
