---
description: Analyze or fix every item of one area in a single warm context; stops at the human push gate.
argument-hint: "analyze|fix <AREA | id,id,...>"
allowed-tools: Read, Write, Edit, Grep, Glob, Task, Bash(git:*), Bash(gh:*), Bash(npm:*), Bash(npx:*), Bash(python:*), Bash(python modules/code-slice/cs.py:*)
model: opus
effort: high
---

# /area-loop

Arguments: `$ARGUMENTS`

Read `workflows/area-loop.md` and follow it exactly for the arguments above. 
Before touching any repo, read its `context/repos/<name>.md` (and the repo's own
`AGENTS.md`/`CLAUDE.md` if present). AGENTS.md guardrails apply throughout.
