---
description: Implement a fix for one work item with regression, horizontal sweep, reviewer round, and (on confirmation) tests, push and PR.
argument-hint: "<id>"
allowed-tools: Read, Write, Edit, Grep, Glob, Task, Bash(git:*), Bash(gh:*), Bash(npm:*), Bash(npx:*), Bash(python:*), Bash(python modules/code-slice/cs.py:*)
model: opus
effort: high
---

# /fix

Arguments: `$ARGUMENTS`

Read `workflows/fix.md` and follow it exactly for the arguments above. 
Before touching any repo, read its `context/repos/<name>.md` (and the repo's own
`AGENTS.md`/`CLAUDE.md` if present). AGENTS.md guardrails apply throughout.
