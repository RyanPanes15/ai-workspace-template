# Workflow: Area loop — drain one area's items in a warm context (optional)

An additive alternative to one-item-at-a-time. **The unit is one area** (a screen and
its dialogs, or a module): items there share files, preconditions, reference code and
navigation, so one warm context is the most cache-efficient unit.

- `analyze-area <AREA | id,id,…>` — run `workflows/analyze.md` per item, sharing one
  context load; optionally auto-run `db-query` for reproducer data and a live
  dev-environment repro per item. Read-only.
- `fix-area <AREA | id,id,…>` — run `workflows/fix.md` Steps 1–8 per item, then a
  verify-until-green loop (Step 9.5 per item), assemble **one review batch** that opens with
  *what I need from you* (approvals, decisions, manual checks), and
  **stop at the human push gate**. On approval: push per item (one PR each), export.
- `fix-queue <area list>` — sequence several area loops hottest-first, **no
  parallelism on a single dev stack**, with a hard token budget per run.

Every run keeps `_work/runs/<area>/TASKS.md` (item × stage); before ending any turn the
agent re-reads it and continues with open, unblocked items. After two automatic nudges
on the same item, mark it blocked and move on.

Rules: autonomous only up to the human gate; per-item records stay under the
canonical workflow names so metrics remain comparable; stop the loop when the budget
or a failed verification is hit and report where it stopped.
