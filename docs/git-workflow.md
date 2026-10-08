# Git / PR orchestration

Used by every mutating workflow (`fix`, `implement-change`, `port-feature`,
`area-loop`) and by ad-hoc work that opens a PR. Only naming varies by task type;
the mechanics do not. Runs **only after the developer confirms** ("push it", "open
the PR", or asks for the PR URL). Do not collapse steps.

Branch/commit/PR naming and integration branches per repo come from the workspace
map in AGENTS.md (generated from `workspace.config.json`).

**10.1 Working-tree pre-flight** — `git -C <repo> status -s`. Unrelated changes →
`[S] stash, push, restore after / [C] cancel`. Stash only on explicit consent.

**10.2 Auth** — prefer an SSH agent or a credential manager. If the agent shell has
no agent, set auth env vars **in the same command** as each network git call — env
vars do not persist between tool calls. Never echo a passphrase or token; delete any
temporary helper at 10.10.

**10.3 Branch** — `git -C <repo> checkout -b <namespace>/<area>/<item-token>`.
Multi-item bundles encode every ID in the branch name.

**10.3.1 Stage-1 lint (PR-wide, once)** — after verification and confirmation, run
`python modules/lint-gate/lint_gate.py <repo> --working-tree --fix`, or the repo's
auto-fixer once over every file the PR touches
(`npx eslint --fix <files>`, `ruff --fix`, `gofmt -w`, …). Unfixable errors → stop.

**10.4 Commit per item** — stage **by name** (never `git add .`/`-A`). Header ≤ 72
chars (count it; the prefix eats ~20). Multi-line bodies via `git commit -F <file>`.
Items sharing a file: reset the shared file, re-apply each item's hunks, commit in
order. **Never `--amend`.**

**10.5 Sync** — `git -C <repo> pull origin <integration-branch>` (merge, not rebase:
rebasing pushed commits forces a force-push later). Conflicts → stop and hand back.

**10.5.1 Stage-2 lint gate** — `python modules/lint-gate/lint_gate.py <repo> <feature-branch>`
(fails on empty diffs / wrong branch / zero files linted), or the repo's diff-based lint (e.g. `lint_check.sh
<feature-branch>`). Check which argument it expects — passing the integration branch
to a script that diffs `origin/<integration>...$1` lints **nothing** and passes.
Zero errors required; fixes are a new `lint fix` commit.

**10.6 Push** — `git -C <repo> push -u origin <branch>`. Pre-push hook failure →
auto-fix, re-run the gate, new commit, retry. Non-fast-forward → back to 10.5.
Never force-push.

**10.7 PR** — `gh pr create --base <integration-branch> --head <branch> --title
"<title>" --body-file <file>` (file avoids shell-quoting damage to code fences and
non-ASCII text). The body's mechanism claims were verified in the reviewer round.

**10.8 Surface the URL** as the first line of the reply.

**10.8.5 Notify (optional, best-effort)** — post to the originating thread only if
the item came from one and the notify module is enabled. Failure never blocks.

**10.8.6 CI checks** — `gh pr checks <n>` (re-check until done). On a failure: read the
failing job's log (`gh run view <run-id> --log-failed`), find the cause, and fix it as a
**new commit** on the PR branch (never amend). Re-run the lint gate and the affected
tests locally. Pushing the fix needs the same confirmation as the original push, unless
the developer approved "push CI fixes to this PR" in advance. A failure unrelated to the
change (flaky test, broken base branch) is reported with evidence, not "fixed" in this PR.

**10.9 Cleanup** — `git -C <repo> checkout <integration-branch>`; `stash pop` if 10.1
stashed; `status -s` back to the pre-fix state.

**10.10 Remove temporary auth helpers.**

Cross-repo: run 10.1–10.10 per repo **in merge order** (API before client when the
client depends on the new API); confirm before opening the second PR.

## Integration-branch notes
- Pass `--base` explicitly; the repo default is often not the integration branch.
- When several integration branches exist (e.g. a change-request line and a defect
  line), check `git diff origin/<a>...origin/<b> -- <files>` before editing and
  record any cherry-pick plan in the PR.
- `git fetch` before concluding a commit is "missing" from a branch.
