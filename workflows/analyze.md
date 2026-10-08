# Workflow: Analyze work item(s) — read-only

**Mode:** defect mode (see AGENTS.md §2). **Tier:** deep @ high.
**Input:** one or more item IDs (e.g. `123`, `BUG-42`, `123,124,130`).
**Output:** per-item analysis + batch summary. **No code edits, no git mutations,
no DB writes.** The only permitted write is a shared-context digest in the session
scratchpad (never a repo file).

---

## Orchestration (always)

**Phase A — shared groundwork (orchestrator, once per batch)**
1. Refresh/load item records (`modules/tracker`, or the source named in the
   workspace map). Dispatch `item-scaffolder` (light) for load + enum lookup +
   translation.
2. Pull all attached evidence (thread transcripts, screenshots, video keyframes,
   log slices) into `_work/evidence/<ID>/`. If a link exists, retrieval is
   mandatory; if attachments fail, check the local folder, then ask — never proceed
   silently without visual evidence the report relies on.
3. Locate files per item (page / form / store / model / API route / service / DB
   object; reference-implementation files if applicable) — `python
   modules/area-index/area_index.py <area>` first, grep only for what it misses. Read each touched repo's
   context once.
4. Write `SHARED_CONTEXT.md` to the scratchpad: file locations, evidence facts,
   per-item one-liners. This is what subagents get — nobody re-reads the same code.

**Phase B — analysis**
- **≥2 items:** cluster by layer / root-cause theme (UI layout, form state, server
  query, cross-cutting). One **read-only** analysis subagent per cluster, dispatched
  in parallel, same tier as the base. Prompt includes: digest path, cluster records,
  exact file pointers, repo context files, "follow workflows/analyze.md Steps 4–12,
  no edits", and the output schema.
- **1 item:** run inline — fanning out one item wastes a round-trip.

**Phase C — synthesis (orchestrator)**
Merge reports, run the cross-item sweep (shared area / module / root cause → one fix
may resolve several), emit the summary table, close any tracking sessions.
Subagents never open/close tracking records.

---

## Per-item steps

### 0. Plan and mistake log
For a batch, write `_work/runs/<batch>/TASKS.md` (one line per item × phase) and tick
as you go; the orchestrator re-reads it before ending a turn.
Read `mistakes/INDEX.md`; open the files whose triggers match this item (§10).

### 1. Status check
Is the item already resolved, duplicated, deployed, or returned for rework? For a
**returned-for-rework** item, read the prior trail (`reports/<ID>-analysis.md`)
first and reconcile against the rejected fix.

### 2. Translate & summarize
Quote the reporter verbatim when the report is the primary evidence (no thread, blank
location field). Translate prose only — keep UI labels, field names, message text,
and identifiers in the original language.

### 3. Validate category
Defect / request / works-as-designed / question / duplicate / environment / task.
A request routes to change mode; works-as-designed routes to a stakeholder reply.

### 4. Repro steps
- Echo reporter steps verbatim when present (prefer the thread over the ticket).
- Otherwise infer **hypothetical** steps, labeled with confidence.
- Shape: a **screen/module reference table** first (name · ID · module · role), then
  **Phase 0 precondition/setup → named phases → Observe**, continuous numbering,
  **one user action per step**, full path from login (menu category → list screen →
  search → select → drill-down → tab/dialog). Every screen written as
  `Name (ID)`. Derive the path from the app's own routing/breadcrumb data, not memory.
- Add a one-step **negative control** that should *not* reproduce.
- Reference-implementation repro (if Tier 2 fires) is a separate block — never
  conflated with the new-system repro.

### 5. Identity check (mandatory, ~2 greps)
Grep 1–2 distinctive literal strings from the report in the owning repo. Output one:
`Identity check: OK — …` / `MISMATCH — report strings found in <file>, item says
<location>; investigating <file>` / `SKIPPED — too generic`.

### 6. Precondition enumeration (before any hypothesis)
State each class, even when "none observed":
- **(0) Curated knowledge** — business map / screen index / ER notes if covered.
- **(a) UI gates** — every flag that disables/hides/enables the element; its setter;
  the data predicate; the required value.
- **(b) Data-load preconditions** — which load branch populates the value; watch
  else-branches that assign defaults (today's date into a hidden field, etc.).
- **(c) Alternate entry paths** — parents that pre-populate state before navigating.
- **(d) Module-scoped state** — mutable bindings outside components are shared by
  every instance.
- **(e) Reset / unmount coverage** — for each store field: resets on load / close /
  unmount, or stale on which transition.

Unknown setter → flag as **known unknown** and recommend a DB/reproducer query.

### 7. Tier 1 — new-code analysis (always)
1. Locate code (index/lookup first, grep fallback). Shared components get extra
   sweep attention. Read it as slices: `cs.py trace <log>` when there is a stack trace,
   `cs.py show file:LINE` for the suspect line, `cs.py flow file#Fn --up 1` for the
   process flow around it (`modules/code-slice`). Open a whole file only when a slice
   is not enough.
2. Hypothesis tied to a **specific predicate** in the precondition table — falsifiable.
3. **Runtime-evidence gate:** runtime-state symptom + static read ⇒ cap at medium.
   HIGH → no test needed (evidence already attached, or deterministic mechanism).
   MEDIUM → *suggest* a self-test. LOW → *run* the self-test
   (`docs/verification-guide.md`) before finalizing. If impossible, say
   "unverified — runtime evidence unavailable because X".
4. **Orphaned-flag check** before an async-race hypothesis: is the computed flag
   actually wired to the control, or shadowed by an inline expression?
5. **Server branch isolation:** bug branch · what selects it · sibling branch ·
   does the selector diverge from the reference?
6. **History pass:** `git log -L <a>,<b>:<file> --no-patch -10`, `git blame -L`.
   A change shortly before the report date is a regression suspect.

### 8. Log inspection (best-effort)
Pull logs for the report date (+1 day, correct timezone, correct environment).
Search SQL identifiers, endpoints, screen IDs, error codes, correlation IDs.
**Absence of expected log lines is evidence** (client-only failures leave no server
trace). Blank error reference on a report is itself a signal of a silent client no-op.

### 9. Historical context (best-effort)
Prior items on the same area/file; prior sweep records for the same pattern.

### 10. Tier 2 — reference comparison (conditional)
**Trigger when any:** report cites prior behavior; calculation / formatting /
rounding / business-rule output; missing field/feature; root cause unclear after a
reasonable look; 1:1 port + behavioral symptom; **default-value divergence** —
empty-string-coerces-to-zero, schema `.default(null)`/optional on a field the
reference always populated, `??`/`||` defaults added in the port, assignment to a
hidden/disabled field in an else-branch, set-then-read-same-closure, component-level
default differing from the reference widget, option list/default index divergence.
**Skip when:** clear stack trace / type error (not a default divergence); pure
cosmetic; new feature; spec-driven change; message wording.

When triggered: locate the reference handler, summarize its contract (inputs,
outputs, rules, null/edge handling, defaults), tabulate old-vs-new defaults, write
the reference repro (same shape as Step 4, final step = *expected*), then **check
the spec-change registry** before calling a difference a regression — a requested
and implemented change is intentional. Believe code evidence over registry labels.

### 11. Decision visibility (mandatory one-liners)
`Reference check: skipped — <reason>` or `triggered — <reason>`;
when triggered: `Spec-change: none | <entry> — verdict → intentional/inconclusive`.
If neither tier resolves it, say so and name what would unblock.

### 12. Sweep pre-flag
Team-flagged sweep need · batch overlap · historical pattern match · catalog pattern
siblings. Flag only — the search itself happens in `workflows/fix.md`.

---

## Output (per item)

```
<ID> — <area> — <category> — <status>
Reporter says: <verbatim or summary> / Translation: …
Identity check: …
Repro steps: <reference table + phases>   Confidence: …
Precondition enumeration: (0)…(e)
Tier 1: <file:line> — hypothesis — predicate — confidence
Branch isolation / History pass: …
Logs: <env> <date> — findings | absence noted
Reference check: … / Spec-change: …
Sweep pre-flag: …
Recommended next step: fix | db-query | stakeholder reply | clarify | self-test
```

Batch summary table: `| ID | Area | Category | Status | Repo | Suspected cause | Confidence |`
plus cross-item clusters.

## Hard rules
- Read-only; subagents read-only (say so in their prompt).
- Precondition table before hypothesis; confidence label mandatory (default medium).
- Identity check and reference-check lines are mandatory.
- Repro blocks: phased, reference table first, one action per step, `Name (ID)`.
- Never skip evidence retrieval as a cost optimization.
