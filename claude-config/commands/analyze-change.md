---
description: Analyze a change request without code changes: requirement reconstruction, impact, collisions, acceptance criteria, estimate.
argument-hint: "CR-<n>[@<area>]"
allowed-tools: Read, Grep, Glob, Bash(git log:*), Bash(git show:*), Bash(git diff:*), Bash(git fetch:*), Bash(git branch:*), Bash(python modules/code-slice/cs.py:*)
model: opus
effort: high
---

# /analyze-change

Arguments: `$ARGUMENTS`

Read `workflows/change-request.md` and follow it exactly for the arguments above. Run **Part 1 — Analyze** only.
Before touching any repo, read its `context/repos/<name>.md` (and the repo's own
`AGENTS.md`/`CLAUDE.md` if present). AGENTS.md guardrails apply throughout.
