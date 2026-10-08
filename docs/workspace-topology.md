# Workspace topology — one workspace, or several?

Start with **one** operational workspace (this template). Split only when a second
audience's concerns clearly diverge. The layout that worked on a long multi-team
engagement:

| Workspace | Holds | Who modifies |
| --- | --- | --- |
| **dev** (this template) | workflows, commands, guardrails, fix tooling; PRs go to the code repos | developers |
| **tester** | test-sweep / bug-filing workflows, QA knowledge, fixtures | testers |
| **admin** | reporting, dashboards, metrics decks, cross-workspace registry, deployment of scheduled jobs | one admin role |

The operational workspaces (dev, tester) each stand alone — a team can do its job
without the other present. The admin workspace is *meta*: tooling **about** both.

## When to split

1. **Don't pre-split.** Wait until concerns diverge: scripts need different deploy
   paths, different credentials, or a different review cadence.
2. **The trigger** is copy-pasting the same script into two workspaces, or writing
   scripts that read from both. That tooling moves to an admin workspace.
3. **Different audiences, different code.** Tester tooling should not appear in dev PRs
   (and vice versa); nightly-report churn should not land in every developer's pull.
4. **Permissions diverge.** Admin tooling touches cloud credentials, the metrics DB
   schema and service accounts at wider scope than most people need.

## How to connect them

- **Sibling repos, not submodules.** Each has its own clone path, access control and
  history. Submodules force a pointer-bump commit on the operational side for every
  admin change.
- **Symlink admin tooling into the operational workspaces** (`<workspace>/admin/ →
  <admin>/<subtree>/`) and gitignore the link, so `python admin/<script>.py` works from
  the operational root. Windows: `mklink /d "<link>" "<target>"` — link first, target
  second (the opposite of `ln -s`); needs an elevated prompt or Developer Mode.
- **Caveat:** a symlink target outside a mounted/sandboxed folder may be unreadable to
  some agents and file tools. When `ls admin/` fails, work in the target directly, and
  `cd "$(realpath admin)"` before running git (changes belong to the admin repo).
- **Register paired files on day one** in `docs/parity.md` and check them with
  `modules/parity/parity_check.py`. Drift between copies is silent and expensive; a
  markdown table is enough until ~30 pairs.
- **Register the sibling workspace in setup** as a `tests` / `other` repo with policy
  `read-only`, so agents here may read its knowledge base but never edit or run git in it.

## Scheduled jobs (dashboards, metrics, alert watchers)

- Keep them in the admin workspace; deploy by `git pull` on the host that runs them.
- Every silent pipeline needs a **dead-man's switch**: a separate check that alerts on
  *state change* when the watcher, tunnel or credentials die. An empty alert channel
  looks exactly like "no errors".
- Every metrics pipeline needs a **coverage check** — who/what produced no data
  (`usage_tracker.py --coverage`). Install steps that fail silently are the norm.
- Document the topology (this file, adapted) in the admin workspace README: new owners
  inherit the mental model, not just the scripts.
