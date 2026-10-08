---
description: Implement a fix for one work item with regression, horizontal sweep, reviewer round, and (on confirmation) tests, push and PR.
argument-hint: "<id>"
allowed-tools: Read, Write, Edit, Grep, Glob, Task, Bash(git:*), Bash(gh:*), Bash(npm:*), Bash(npx:*), Bash(python:*), Bash(python modules/code-slice/cs.py:*)
effort: high
---

# /fix

Arguments: `$ARGUMENTS`

**Tier gate (deep).** If this session was not started as a deep session — the model
you are running as is not opus-class (`CLAUDE.md` §Session shapes) — stop before any
other step and ask the developer to start a deep session (`claude --model opus --effort high`,
or `/clear`, `/model opus`, `/effort high` in a running process), then re-run.
Never switch model mid-session yourself. Effort comes from this command's frontmatter.

Read `workflows/fix.md` and follow it exactly for the arguments above. 
Before touching any repo, read its `context/repos/<name>.md` (and the repo's own
`AGENTS.md`/`CLAUDE.md` if present). AGENTS.md guardrails apply throughout.
