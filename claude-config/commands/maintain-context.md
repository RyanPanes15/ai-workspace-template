---
description: Fold recent corrections into AGENTS.md / workflows / playbooks, prune, and check model-routing drift.
argument-hint: "[--since YYYY-MM-DD]"
allowed-tools: Read, Write, Edit, Grep, Glob, Bash(git log:*), Bash(python:*), Bash(python modules/code-slice/cs.py:*)
effort: high
---

# /maintain-context

Arguments: `$ARGUMENTS`

**Tier gate (deep).** If this session was not started as a deep session — the model
you are running as is not opus-class (`CLAUDE.md` §Session shapes) — stop before any
other step and ask the developer to `/clear`, `/model opus`, `/effort high`, then re-run.
Never switch model mid-session yourself. Effort comes from this command's frontmatter.

Read `workflows/maintain-context.md` and follow it exactly for the arguments above. 
Before touching any repo, read its `context/repos/<name>.md` (and the repo's own
`AGENTS.md`/`CLAUDE.md` if present). AGENTS.md guardrails apply throughout.
