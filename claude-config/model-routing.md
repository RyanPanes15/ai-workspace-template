# Model Routing Catalog

Source of truth for which tier each unit runs on. The catalog **justifies**; the
**session shape** (`CLAUDE.md` §Session shapes) plus each deep command's tier gate
**selects** the model; command frontmatter pins **effort** only; the usage ledger
(`modules/usage-metrics`) **audits** actual against intended. Drift is silent — audit.

Tiers are tool-neutral. Claude mapping: **deep = opus**, **standard = sonnet**,
**light = haiku**. Use aliases, not pinned model IDs, so routing survives upgrades.
Other tools: map deep/standard/light to your provider's equivalents.

## Why the model is not pinned per command

The prompt cache is per model and matches from the first token. A command whose
frontmatter names a different model is a model switch for that turn: the whole
conversation is re-read with no cache hits, and again when the session model resumes
on the next prompt. The cost scales with the context at that moment, so a `/fix` after
an hour of chat is the most expensive possible way to start a fix. Subagents are
different: each has its own context and cache, so their frontmatter `model` is free.

Effort pins stay on commands: on current models (Opus 5.5, Sonnet 5.5, Haiku 5.5,
Fable 5.1, with an API key or subscription) an effort change keeps the cache. On older
models, Bedrock, Google Cloud's Agent Platform or an apps gateway it does not — there,
set effort once per session and expect a command's `effort:` to cost one re-read.

## Session shapes

Set at launch: `claude --model opus --effort high` (deep) or `claude --model sonnet
--effort medium` (triage). Both flags are session-only and save nothing. Inside a running
process the fallback is `/clear` → `/model` → `/effort`, in both directions — `/clear` is
not documented to reset the model. `/model` saves to user settings unless applied with
`s`; the project `settings.json` `model` outranks that saved value at the next startup.

| Shape | Model · effort | Units |
| --- | --- | --- |
| Deep | opus · high | `/analyze`, `/analyze-change`, `/fix`, `/implement-change`, `/review-pr`, `/port-feature`, `/build`, `/scaffold-project`, `/area-loop`, `/maintain-context` |
| Triage (floor) | sonnet · medium | `/brief`, `/log-triage`, `/db-query`, `/stakeholder-reply`, `/adr`, `/repo-overview`, `/setup-workspace`, `/export`, ad-hoc chat |

Light units (`/export`, metrics, formatting) run at the session's model and dispatch
their writing to a light subagent, so the cheap tier is kept in either shape.

## Catalog

| Unit | Tier | Effort | Rationale |
| --- | --- | --- | --- |
| `/export`, metrics, `item-scaffolder`, `report-formatter`, `test-runner` | light | — | assemble/format/run existing content; deterministic |
| `/brief` | standard | medium | intake: decides which deep command runs, so it runs cheap and first; writes a file the command starts cold from |
| `/log-triage` | standard | medium | clustering is mechanical; per-issue code check is verifiable |
| `/db-query` | standard | medium | interactive SQL; escalate hard reproducer searches |
| `/stakeholder-reply` | standard | medium | short, but external text — accuracy gate vetoes light |
| ad-hoc chat (session default) | standard | medium | workhorse floor; hard ad-hoc work gets a deep session, not a mid-session switch |
| `/analyze`, `/analyze-change` | deep | high | root cause under uncertainty |
| `/review-pr` | deep | high | adversarial merge-blocking review; a missed blocker ships |
| `/fix`, `/implement-change` | deep | high | ships code; cross-layer rework is the costly failure |
| `/build`, `/scaffold-project` | deep | high | ships new code and structure that later work builds on |
| `/adr` | standard | medium | drafting from a decided conversation |
| `/repo-overview` | standard | medium | documents existing files; every fact traced to a file and diagrams render-checked |
| `/port-feature` | deep | high | silent rule omission is the failure mode |
| `/area-loop` | deep | high | wraps analyze/fix/port; inherits their routing |
| `/maintain-context` | deep | high | edits files that shape every future session |
| `fix-reviewer`, `fix-verifier`, `completeness-verifier` | deep | high | the adversarial safety net; own context, so the probes never ride along in the main session |

## Stage-level dispatch

Deep workflows keep a deep base (the reasoning core is never downgraded) and send
only mechanical stages to cheaper subagents, whose output is the only thing that enters
the main context:

- analyze: load/enum/translate → `item-scaffolder` (light); per-cluster analysis →
  parallel read-only subagents at the **same** tier; report → `report-formatter`.
- fix: anchor re-verification + edit specs → read-only subagents (standard);
  tests / lint / build runs → `test-runner` (light, failures + counts only);
  full reviewer round → `fix-reviewer` (deep, returns verdict + attacks table + evidence
  path; the reduced copy-only round stays inline); cross-layer check → `fix-verifier`
  (deep, dispatched by the main agent after the reviewer returns); report → `report-formatter`; git/PR
  orchestration inline (tool calls, not reasoning).
- port: pattern extraction + scaffolding → standard; inventory, logic drafting,
  verification → deep.

## Subagent brief

Every ad-hoc dispatch (the per-cluster analysis agents, the anchor / edit-spec agents in
fix, the pattern-extraction agents in port) is composed from the same fields; the named
agents in `.claude/agents/` carry them in their "Inputs" paragraph:

- **Objective** — one sentence, the question or artifact.
- **Starting state** — digest path, files or file:line pointers, branch, repo context
  files, quiet commands.
- **Target state** — the artifact to return and its schema (failures + counts, verdict
  table, edit specs, …).
- **Scope** — read-only or not; which repos and directories; do-not-touch list.
- **Stop conditions** — when to return early; never commit, push or mutate the shared
  tree; what needs the developer goes under `needs developer:`.
- **Progress evidence** — every claim cites a tool result or a file:line read in this
  run; "no error" alone is not a pass.

Ask for conclusions, evidence and checks, never for the subagent's reasoning.

## Effort

- Effort and tier are orthogonal dials. Steady state: deep @ high, standard @
  medium, light @ n/a (some light models ignore effort).
- **Don't starve agentic units** — higher effort up front often cuts turn count and
  total cost. Savings come from the standard/light units and the session floor. The
  price-sheet gap between tiers shrinks in long sessions (cache reads dominate); what
  decides cost per finished item is turns to finish, so judge routing by cost per
  passed item in the ledger, not by the price sheet.
- `ultrathink` deepens one turn without a model switch (likely cache-safe; verify).

## Escalation

Triggers: returned-for-rework items, cross-repo + cross-layer fixes, a hypothesis
already refuted once, a first failed real check (compile, first test, wrong files),
genuinely ambiguous multi-area batches. Decide **early**, while the context is small.

How: **new session + trail**, never the transcript. Write the handoff (the item, the
verdict so far, the failing check, the files that matter, open questions) to
`reports/<ID>-analysis.md` or `_work/runs/<task>/HANDOFF.md`, tell the developer, and
let them `/clear` into a deep session. If a mid-session switch is unavoidable,
`/compact` first so the re-read is small.

## Fallback

- Deep units falling back to standard: **surface** a one-line notice (trust in a root
  cause depends on the tier).
- Standard units: fall back **up**, surface (cost spike, quality safe). Never silently
  fall to light.
- Light units: fall back to standard silently, with a log line.
- A fallback keeps the unit's effort only up to the new model's ceiling: a deep unit
  at an effort level the standard model lacks runs at that model's highest level.

## Audit

If `modules/usage-metrics` is enabled, run `usage_tracker.py --report` weekly and
compare against this table: per-unit model share (a deep command that ran on sonnet
means a skipped tier gate), **cache-read share** per session and user (low = the
prefix keeps breaking: switches or long gaps), **cold requests** per command (model
flips), and context growth per session (an ever-climbing curve = a session that
should have been cleared), and per-unit **effort** against the catalog's Effort
column. The ledger is the only place that shows it. Optional spend alerts:
`usage_metrics.alert_usd_per_day` in `workspace.config.json`.

**Downgrade gate.** Before lowering a unit's tier or effort, run it on 3–5 recent real
inputs at both settings and compare: the same verdicts and checks passing, and lower
`$/pass` (cost per passed item, not per turn). Any lost verdict or extra failed check
keeps the current setting. Record the comparison in the change's reason.
