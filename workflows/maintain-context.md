# Workflow: Maintain the agent context (monthly, or after a rework-heavy week)

**Tier:** deep @ high — these files shape every future session; over-trimming removes
guardrails. Edits here need developer approval before commit.

0. **Review `mistakes/`.** For each file: occurrences ≥ 3 or severity high → propose
   promoting its rule into AGENTS.md / the workflow step where the decision is made;
   merge files that describe the same class; retire files whose cause was removed
   (tooling fixed) with a note; confirm INDEX.md lists every file and nothing else.
1. **Collect corrections.** Scan recent `reports/*-analysis.md`, evidence files, and
   review comments for: retracted root causes, reverted fixes, returned-for-rework
   items, reviewer findings, "invalid trial" notes.
2. **Classify each** into a failure mode (e.g. static read of runtime bug, wrong
   environment, name-keyed sweep, unverified premise, stale anchor, cross-layer miss).
3. **Promote recurring modes** (≥2 occurrences) into a rule: generalized sentence +
   one worked example with the item ID. Put it where the decision is made:
   AGENTS.md (cross-cutting), a workflow step (procedural), `docs/verification-guide.md`
   (probe/tooling traps), `context/repos/<name>.md` (repo-specific pattern).
4. **Prune.** Merge duplicates, drop rules that never fire, move long examples to
   `docs/lessons-catalog.md`. Target: AGENTS.md stays under ~400 lines.
5. **Check routing drift.** Compare actual model share per workflow (usage ledger, if
   enabled) against `.claude/model-routing.md`; fix frontmatter or the catalog.
6. **Diff review.** Present the proposed context diff with the reason for each change.
