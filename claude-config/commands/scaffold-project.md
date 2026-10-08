---
description: Bootstrap a new repo for a greenfield project — stack ADR, skeleton with lint/typecheck/test/build/CI, cross-cutting basics; creating remotes and pushing need consent.
argument-hint: "[repo-name]"
allowed-tools: Read, Write, Edit, Grep, Glob, Bash(git:*), Bash(npm:*), Bash(npx:*), Bash(python:*), Bash(python modules/code-slice/cs.py:*)
effort: high
---

# /scaffold-project

Arguments: `$ARGUMENTS`

**Tier gate (deep).** If this session was not started as a deep session — the model
you are running as is not opus-class (`CLAUDE.md` §Session shapes) — stop before any
other step and ask the developer to `/clear`, `/model opus`, `/effort high`, then re-run.
Never switch model mid-session yourself. Effort comes from this command's frontmatter.

Read `workflows/scaffold-project.md` and follow it exactly.
