---
description: Implement an analyzed change request; asks the target branch every time; PR on confirmation.
argument-hint: "CR-<n>@<area>"
allowed-tools: Read, Write, Edit, Grep, Glob, Task, Bash(git:*), Bash(gh:*), Bash(npm:*), Bash(npx:*), Bash(python modules/code-slice/cs.py:*)
effort: high
---

# /implement-change

Arguments: `$ARGUMENTS`

**Tier gate (deep).** If this session was not started as a deep session — the model
you are running as is not opus-class (`CLAUDE.md` §Session shapes) — stop before any
other step and ask the developer to `/clear`, `/model opus`, `/effort high`, then re-run.
Never switch model mid-session yourself. Effort comes from this command's frontmatter.

Read `workflows/change-request.md` and follow it exactly for the arguments above. Run **Part 2 — Implement**.
Before touching any repo, read its `context/repos/<name>.md` (and the repo's own
`AGENTS.md`/`CLAUDE.md` if present). AGENTS.md guardrails apply throughout.
