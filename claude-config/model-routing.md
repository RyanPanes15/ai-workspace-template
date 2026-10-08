# Model Routing Catalog

Source of truth for which tier each unit runs on. The catalog **justifies**; command
and agent frontmatter **enforces**. Keep them in sync — drift is silent.

Tiers are tool-neutral. Claude mapping: **deep = opus**, **standard = sonnet**,
**light = haiku**. Use aliases, not pinned model IDs, so routing survives upgrades.
Other tools: map deep/standard/light to your provider's equivalents.

## Catalog

| Unit | Tier | Effort | Rationale |
| --- | --- | --- | --- |
| `/export`, metrics, `item-scaffolder`, `report-formatter` | light | — | assemble/format existing content; deterministic |
| `/log-triage` | standard | medium | clustering is mechanical; per-issue code check is verifiable |
| `/db-query` | standard | medium | interactive SQL; escalate hard reproducer searches |
| `/stakeholder-reply` | standard | medium | short, but external text — accuracy gate vetoes light |
| ad-hoc chat (session default) | standard | medium | workhorse floor; bump manually for hard ad-hoc work |
| `/analyze`, `/analyze-change` | deep | high | root cause under uncertainty |
| `/review-pr` | deep | high | adversarial merge-blocking review; a missed blocker ships |
| `/fix`, `/implement-change` | deep | high | ships code; cross-layer rework is the costly failure |
| `/build`, `/scaffold-project` | deep | high | ships new code and structure that later work builds on |
| `/adr` | standard | medium | drafting from a decided conversation |
| `/repo-overview` | standard | medium | documents existing files; every fact traced to a file and diagrams render-checked |
| `/port-feature` | deep | high | silent rule omission is the failure mode |
| `/area-loop` | deep | high | wraps analyze/fix; inherits their routing |
| `/maintain-context` | deep | high | edits files that shape every future session |
| `fix-verifier`, `completeness-verifier` | deep | high | the adversarial safety net |

## Stage-level dispatch

Deep workflows keep a deep base (the reasoning core is never downgraded) and send
only mechanical stages to cheaper subagents:

- analyze: load/enum/translate → `item-scaffolder` (light); per-cluster analysis →
  parallel read-only subagents at the **same** tier; report → `report-formatter`.
- fix: anchor re-verification + edit specs → read-only subagents (standard);
  cross-layer check → `fix-verifier` (deep); report → `report-formatter`; git/PR
  orchestration inline (tool calls, not reasoning).
- port: pattern extraction + scaffolding → standard; inventory, logic drafting,
  verification → deep.

## Effort

- Effort and tier are orthogonal dials. Steady state: deep @ high, standard @
  medium, light @ n/a (some light models ignore effort).
- **Don't starve agentic units** — higher effort up front often cuts turn count and
  total cost. Savings come from the standard/light units and the session floor.
- `ultrathink` deepens one turn. Escalating to a higher tier is a manual,
  per-invocation decision for: returned-for-rework items, cross-repo + cross-layer
  fixes, hypotheses already refuted once, genuinely ambiguous multi-area batches.

## Fallback

- Deep units falling back to standard: **surface** a one-line notice (trust in a root
  cause depends on the tier).
- Standard units: fall back **up**, surface (cost spike, quality safe). Never silently
  fall to light.
- Light units: fall back to standard silently, with a log line.

## Audit

If `modules/usage-metrics` is enabled, compare actual per-unit model share against
this table weekly. A standard-tier session default can still end up running almost
everything on deep (manual `/model` switches persist across turns) — the ledger is
the only place that shows it.
