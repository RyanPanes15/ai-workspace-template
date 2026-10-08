---
description: Analyze a change request without code changes: requirement reconstruction, impact, collisions, acceptance criteria, estimate.
argument-hint: "CR-<n>[@<area>]"
allowed-tools: Read, Write, Grep, Glob, Bash(git log:*), Bash(git show:*), Bash(git diff:*), Bash(git fetch:*), Bash(git branch:*), Bash(python modules/code-slice/cs.py:*)
effort: high
---

# /analyze-change

Arguments: `$ARGUMENTS`

**Tier gate (deep).** If this session was not started as a deep session — the model
you are running as is not opus-class (`CLAUDE.md` §Session shapes) — stop before any
other step and ask the developer to start a deep session (`claude --model opus --effort high`,
or `/clear`, `/model opus`, `/effort high` in a running process), then re-run.
Never switch model mid-session yourself. Effort comes from this command's frontmatter.

Read `workflows/change-request.md` and follow it exactly for the arguments above. Run **Part 1 — Analyze** only.
Before touching any repo, read its `context/repos/<name>.md` (and the repo's own
`AGENTS.md`/`CLAUDE.md` if present). AGENTS.md guardrails apply throughout.
