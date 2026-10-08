---
description: Export an item's analysis trail and fix summary to reports/ as markdown, with git change footprint.
argument-hint: "<id> [notes]"
allowed-tools: Read, Write, Grep, Bash(git log:*), Bash(git show:*), Bash(git diff:*)
model: haiku
---

# /export

Arguments: `$ARGUMENTS`

Read `workflows/export.md` and follow it exactly for the arguments above. 
Before touching any repo, read its `context/repos/<name>.md` (and the repo's own
`AGENTS.md`/`CLAUDE.md` if present). AGENTS.md guardrails apply throughout.
