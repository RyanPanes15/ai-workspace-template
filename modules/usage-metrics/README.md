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
`python modules/usage-metrics/usage_tracker.py --report [--by item|model]`.
