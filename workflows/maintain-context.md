# Workflow: Maintain the agent context (monthly, or after a rework-heavy week)

**Tier:** deep @ high — these files shape every future session; over-trimming removes
guardrails. Edits here need developer approval before commit.

0. **Read the ledger.** `docs/context-ledger.md` lists the sources earlier runs
   processed and the patterns they promoted, rejected or deferred (with reasons).
   Process only sources not listed; don't re-propose a rejected pattern unless new
   evidence meets the reason it was rejected for.
1. **Review `mistakes/`.** For each file: occurrences ≥ 3 or severity high → propose
   promoting its rule into AGENTS.md / the workflow step where the decision is made;
   merge files that describe the same class; retire files whose cause was removed
   (tooling fixed) with a note; confirm INDEX.md lists every file and nothing else.
2. **Collect corrections.** Scan recent `reports/*-analysis.md`, evidence files, and
   review comments for: retracted root causes, reverted fixes, returned-for-rework
   items, reviewer findings, "invalid trial" notes, questions the agent asked whose
   answer was already in context (or was answered before but never written down), and
   repeated discovery sequences (many exploratory tool calls to learn one fact).
3. **Classify each** into a failure mode (e.g. static read of runtime bug, wrong
   environment, name-keyed sweep, unverified premise, stale anchor, cross-layer miss,
   asked an answered question, exploratory waste).
4. **Promote recurring modes** (≥2 occurrences) into a rule: generalized sentence +
   one worked example with the item ID. A pattern seen once but with high blast radius
   (security, data integrity, production safety) is promoted immediately.
   - Place it by coverage and kind: one repo → `context/repos/<name>.md`; two or more
     repos → AGENTS.md (cross-cutting) or the workflow step (procedural);
     probe/tooling traps → `docs/verification-guide.md`. A pattern from a repo's own
     agent file that two or more repos share counts as cross-cutting.
   - Prefer a test, lint rule, hook or command step when one would enforce it; add
     a rule only when none fits.
   - Write it as a directive in imperative voice. When the developer's correction
     phrases it cleanly, use their words.
   - Search the target file first: a duplicate is dropped; a correction that
     contradicts an existing rule means that rule may be stale — surface both, don't
     silently flip it.
5. **Inventory.** List every context file with line and token counts: always-loaded
   (CLAUDE.md, AGENTS.md, command/agent/skill descriptions, `~/.claude/CLAUDE.md`),
   path-scoped (`.claude/rules/repo-*.md`), per repo (`context/repos/*.md`, the repos'
   own `AGENTS.md`/`CLAUDE.md`) and local (`*.local.md`). Edit sources only:
   `.claude/rules/` is generated from `context/repos/` (`--render`), and repos' own
   files change only by a developer PR under their repo policy.
6. **Prune.**
   - Deduplicate across layers first (personal ↔ AGENTS.md ↔ `context/repos/`), then
     within files. Move a rule at the wrong level; don't delete it.
   - Drop rules that never fire, restate the model's default behavior, or repeat
     what the repo already states (package.json, tsconfig, README).
   - For each cut, name the output that would change without the line; if you can,
     compress instead of cutting. Compress: imperative voice, no hedges ("generally",
     "try to", "consider"), rationale only when it changes how the rule applies.
   - Move long examples to `docs/lessons-catalog.md`. Target: AGENTS.md stays under
     ~300 lines excluding the generated map and profile blocks **and** the
     always-loaded total (`/context`: CLAUDE.md + AGENTS.md + command, agent and
     skill descriptions) stays under ~8K tokens — record the figure in the run's
     TASKS.md. Anything a workflow re-loads at the moment it is needed is a candidate
     to move out (`/claude-api prompt-audit` helps find it); evidence rules and
     guardrails stay.
7. **Check integration drift.** Every command, agent, hook, workflow, module and path
   named in AGENTS.md, CLAUDE.md, `claude-config/commands/*.md` and `workflows/*.md`
   exists; every command and agent is listed where CLAUDE.md and
   `claude-config/model-routing.md` list them.
8. **Check routing and cache drift.** `usage_tracker.py --report --by model` against
   `.claude/model-routing.md`: a deep command on the standard tier = a skipped tier
   gate; `--report` cache% below ~80% or many cold requests per command = mid-session
   model switches or sessions left to expire; `--by session` growth that never resets =
   sessions that should have been cleared. Fix the catalog, the session-shape text, or
   the habit — then `$/pass` per model (same report) decides whether the routing pays.
   A proposed tier or effort downgrade passes the downgrade gate
   (`model-routing.md` §Audit) before it lands.
9. **Diff review.** Present the proposed context diff with the reason for each change,
   plus 3–5 representative prompts (one per affected workflow) run against the old and
   new context, with any output that changed.
10. **Update the ledger** (after approval): append the run date, the sources processed,
    each promoted pattern with its evidence, and each rejected or deferred pattern with
    the reason ("2 occurrences, one repo, low blast radius — defer to a third").
