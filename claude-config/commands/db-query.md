---
description: Read-only DB investigation for a work item (investigation or reproducer-data mode).
argument-hint: '<id> [question | "find repro data for <UI state>"]'
allowed-tools: Read, Grep, Glob, Bash(python modules/db-query/run_query.py:*), Bash(python modules/code-slice/cs.py:*)
model: sonnet
effort: medium
---

# /db-query

Arguments: `$ARGUMENTS`

Read `workflows/db-query.md` and follow it exactly for the arguments above. 
Before touching any repo, read its `context/repos/<name>.md` (and the repo's own
`AGENTS.md`/`CLAUDE.md` if present). AGENTS.md guardrails apply throughout.
