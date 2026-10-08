---
description: Fold recent corrections into AGENTS.md / workflows / playbooks, prune, and check model-routing drift.
argument-hint: "[--since YYYY-MM-DD]"
allowed-tools: Read, Write, Edit, Grep, Glob, Bash(git log:*), Bash(python:*), Bash(python modules/code-slice/cs.py:*)
model: opus
effort: high
---

# /maintain-context

Arguments: `$ARGUMENTS`

Read `workflows/maintain-context.md` and follow it exactly for the arguments above. 
Before touching any repo, read its `context/repos/<name>.md` (and the repo's own
`AGENTS.md`/`CLAUDE.md` if present). AGENTS.md guardrails apply throughout.
