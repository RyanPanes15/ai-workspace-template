# pr-metrics module (optional)

`fetch_pr_history.py` pulls PR history for the workspace's GitHub repos through `gh`
(cached in `_work/pr-history.json`) and summarises opened / merged / median time to
merge / line counts / share of PRs with an AI `Co-Authored-By` trailer, per repo and
per person (names canonicalised via `context/people.json`). Combine with the usage
ledger for cost per merged PR. Read-only.
