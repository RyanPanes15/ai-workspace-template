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
   `docs/lessons-catalog.md`. Target: AGENTS.md stays under ~300 lines excluding the generated map and profile blocks **and** the
   always-loaded total (`/context`: CLAUDE.md + AGENTS.md + command, agent and skill
   descriptions) stays under ~8K tokens — record the figure in the run's TASKS.md.
   Anything a workflow re-loads at the moment it is needed is a candidate to move out
   (`/claude-api prompt-audit` helps find it); evidence rules and guardrails stay.
5. **Check routing and cache drift.** `usage_tracker.py --report --by model` against
   `.claude/model-routing.md`: a deep command on the standard tier = a skipped tier
   gate; `--report` cache% below ~80% or many cold requests per command = mid-session
   model switches or sessions left to expire; `--by session` growth that never resets =
   sessions that should have been cleared. Fix the catalog, the session-shape text, or
   the habit — then `$/pass` per model (same report) decides whether the routing pays.
6. **Diff review.** Present the proposed context diff with the reason for each change.
