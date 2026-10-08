# Workflow: Export an item's analysis trail

**Tier:** light. **Input:** item ID. Documentation only — no new analysis, no grep,
no tracking writes. Uses only what exists in the current session and on disk.

## Files (all markdown, in `reports/`)
- `reports/<ID>-analysis.md` — **append-only**; each run adds a dated section
  (`workflows/analyze.md` Phase D writes the first one; `fix.md` Step 11 appends).
- `reports/<ID>-bugs-and-fixes.md` — **overwrite-on-regenerate**; reflects the current
  shipped state: summary, repro (phased, reference table first), root cause, a
  1–2 sentence **plain-language root-cause summary** (no paths/IDs; stakeholder-safe),
  fix, change footprint, verification evidence link, PR links.
- Optional stakeholder summary pair (e.g. EN + second language) when the item source
  requires it (configure in `workspace.config.json` → `export.summary_languages`).

## Change footprint
Collected from git at export time (`git show --numstat`, `git diff --stat`), per repo;
lint commits on their own row; uncommitted work labeled "working tree". Printed in the
reply as well as written. Never estimated from the session's edits.

## Outcome marker
Record the item's outcome in the ledger when the usage-metrics module is on, so cost
per *passed* item can be reported:
`python modules/usage-metrics/usage_tracker.py --outcome <ID> pass|fail|open`
(`pass` = verified and merged/accepted; `fail` = reverted or returned for rework;
`open` = still in progress). Also put `Outcome: <value>` in the header of
`reports/<ID>-bugs-and-fixes.md`.

## Integrity pass (mandatory, before confirming)
1. Code, file:line, identifiers, hashes, tags re-read from the artifact — not memory.
2. Verdicts agree across every file written (category, root cause, fix state).
3. No leftover deliberation text; a correction is applied everywhere, not appended.
4. **Credential scan** of every written file (local notes, tokens, connection strings)
   — replace with `[REDACTED]`. The prohibition is not self-enforcing; grep.

Hashes come from `git log` verbatim. Preserve cited paths exactly. Never name an
implementer or blame a prior commit in stakeholder-facing sections.
