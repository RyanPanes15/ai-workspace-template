---
description: Build a feature from a spec — spec, design note (ADR when costly to reverse), tests, small commits, verification evidence per acceptance criterion, self-review; PR on confirmation.
argument-hint: "<feature-name | docs/specs/<file>.md>"
allowed-tools: Read, Write, Edit, Grep, Glob, Task, Bash(git:*), Bash(gh:*), Bash(npm:*), Bash(npx:*), Bash(python:*), Bash(python modules/code-slice/cs.py:*)
effort: high
---

# /build

Arguments: `$ARGUMENTS`

**Tier gate (deep).** If this session was not started as a deep session — the model
you are running as is not opus-class (`CLAUDE.md` §Session shapes) — stop before any
other step and ask the developer to start a deep session (`claude --model opus --effort high`,
or `/clear`, `/model opus`, `/effort high` in a running process), then re-run.
Never switch model mid-session yourself. Effort comes from this command's frontmatter.

Read `workflows/build.md` and follow it exactly.
