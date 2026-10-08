# Cross-workspace parity registry

Use when this workspace has a sibling workspace (e.g. a tester or admin workspace)
and some files must stay aligned between them. Drift between copies is silent and
expensive; this file says which copies must match and how. Check it with
`python modules/parity/parity_check.py` (reads the tables below).

Default for any new file: **workspace-specific** — no entry. Add an entry only when
two copies must actively align. Keep it small (~20 rows); past ~50, things are
over-coupled or entries are stale.

## Relationship types

- **Byte-identical** — must match exactly (line endings normalized). Drift is a bug;
  edit the source-of-truth side and copy to the others in the same change.
- **Mirrored** — same job, different shape. Only the `check` aspect (a regex whose
  matches must be the same on both sides) has to align; everything else may differ.
- **Shared-name-only** — same path, unrelated purpose. Listed so nobody "fixes" it.
- **Single source** — one physical file reached through a symlink or shared clone.

## Workspaces

| name | root | notes |
| --- | --- | --- |
| dev | . | this workspace |
<!-- | test | ../my-tester-workspace | sibling clone | -->

## Byte-identical

`path` is the same relative path in every listed workspace (blank `workspaces` = all),
or an explicit mapping `dev:tools/run_query.py = test:run_query.py`. A directory
compares every file under it.

| path | workspaces | source of truth | notes |
| --- | --- | --- | --- |
<!-- | modules/db-query/run_query.py | dev,test | dev | SELECT-only wrapper | -->

## Mirrored

| path | workspaces | check | notes |
| --- | --- | --- | --- |
<!-- | fetch-all.py | dev,test | `--only|--list|PYTHONUTF8` | runner mechanics align; fetcher list differs | -->

## Shared-name-only

| path | notes |
| --- | --- |

## Single source

| path | notes |
| --- | --- |

## Scan

Globs checked for **unregistered** pairs (same relative path in 2+ workspaces, not
listed above):

```
*.py
modules/**/*.py
.claude/commands/*.md
*.json
```

## Changelog

| date | change |
| --- | --- |
