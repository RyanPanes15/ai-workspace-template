# usage-metrics module (optional)

Per-turn ledger (`reports/usage.jsonl`) of tokens, estimated cost, model family,
workflow command and item IDs. Use it to:
- see which items and workflows consume the most effort;
- audit model routing — the only reliable signal that a "standard" default is
  actually running everything on the deep tier;
- size estimates for similar future items.

Enable with setup (adds a Stop hook to `.claude/settings.local.json`), restart the
agent, then **verify a line appears** after your next reply — a silent install that
never records is the most common failure. Report:
`python modules/usage-metrics/usage_tracker.py --report [--by command|item|user|session|model]`.

Every row carries the cache signals from the talk/post this template follows:
**cache%** (reads / all input — low means the prefix keeps breaking), **cold/req**
(requests that rebuilt the cache: a model switch, an expired cache, a fresh session),
**ctx_max** (largest request; `--by session` prints its growth). `--by model` adds the
per-model table: items, passed, average turns, $/turn and **$/pass** — the number that
decides routing, not the price sheet. Mark outcomes after export:
`python modules/usage-metrics/usage_tracker.py --outcome <ID> pass|fail|open`.
Rates are estimates from `workspace.config.json → usage_metrics.rates` (defaults in the
script; verify against the pricing page).
