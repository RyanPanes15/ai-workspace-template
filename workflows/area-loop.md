# Workflow: Area loop — drain one area's items in a warm context (optional)

An additive alternative to one-item-at-a-time. **The unit is one area** (a screen and
its dialogs, or a module): items there share files, preconditions, reference code and
navigation, so a warm context saves re-reading them. That saving is bounded; the
growing prefix is not — every turn re-sends everything so far, so the loop runs under a
**numeric budget** and hands over through a digest, never through an endless session.

- `analyze-area <AREA | id,id,…>` — run `workflows/analyze.md` per item, sharing one
  context load; optionally auto-run `db-query` for reproducer data and a live
  dev-environment repro per item. Read-only apart from the trail files.
- `fix-area <AREA | id,id,…>` — run `workflows/fix.md` Steps 1–8 per item, then a
  verify-until-green loop (Step 9.5 per item, test runs through `test-runner`),
  assemble **one review batch** that opens with *what I need from you* (approvals,
  decisions, manual checks), and **stop at the human push gate**. On approval: push
  per item (one PR each), export.
- `fix-queue <area list>` — sequence several area loops hottest-first, **no
  parallelism on a single dev stack**.

## Budget and digest

1. At start, write `_work/runs/<area>/TASKS.md` (item × stage) with the run's
   **budget as numbers**: max items this session (default 3) and a context ceiling
   (default ~150K tokens, or whatever `/context` shows is sensible for this stack).
2. After each item, write `_work/runs/<area>/<ID>.md` — the digest the next item needs
   (shared preconditions, file anchors, reference code already read, environment
   facts) — and the item's trail per `analyze.md` Phase D / `fix.md` Step 11.
3. **When the budget is hit, stop**: write `_work/runs/<area>/DIGEST.md` (the merged
   per-item digests plus the resume pointer: next item, its stage, open questions),
   report where it stopped, and tell the developer to `/compact` or `/clear` and
   resume with `/area-loop <mode> <AREA>` — the next run reads `DIGEST.md` first and
   re-verifies its anchors before use.
4. Before stopping at the human push gate, write `DIGEST.md` too: the developer may
   step away past the cache window, and the loop must be resumable from disk.
5. Alternative shape for independent items: one `fix` subagent per item, each started
   from the digest, so the parent context holds only the reports. AGENTS.md §4's
   "one subagent per root-cause cluster" is an analysis-clustering rule; a fix loop
   over independent items may use one per item when the digest carries the shared
   context.

Before ending any turn the agent re-reads `TASKS.md` and continues with open,
unblocked items. After two automatic nudges on the same item, mark it blocked and
move on.

Rules: autonomous only up to the human gate; per-item records stay under the
canonical workflow names so metrics remain comparable; stop the loop when the budget
or a failed verification is hit and report where it stopped; never switch model
mid-run (a deep session is the precondition, see the command's tier gate).
