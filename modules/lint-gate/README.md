# lint-gate module

`lint_gate.py <repo> [feature-branch]` lints only the files the PR changes and
**fails on every vacuous case**: integration branch passed as the feature, missing
`origin/<base>`, empty diff, report not rewritten, zero files linted. Configure the
linter per repo under `repos[].lint` in `workspace.config.json` (defaults: ESLint,
checkstyle report). `--working-tree --fix` runs the Stage-1 auto-fix before commits.
Used by `docs/git-workflow.md` 10.3.1 and 10.5.1.
