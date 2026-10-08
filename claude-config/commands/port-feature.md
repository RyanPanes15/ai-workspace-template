---
description: Port a screen/feature from the reference implementation with a logic inventory and adversarial completeness verification.
argument-hint: "<area-id> [--audit-only]"
allowed-tools: Bash(python modules/port-status/port_status.py:*), Bash(python modules/area-index/area_index.py:*), Read, Write, Edit, Grep, Glob, Task, Bash(git:*), Bash(npm:*), Bash(npx:*), Bash(python modules/code-slice/cs.py:*)
effort: high
---

# /port-feature

Arguments: `$ARGUMENTS`

**Tier gate (deep).** If this session was not started as a deep session — the model
you are running as is not opus-class (`CLAUDE.md` §Session shapes) — stop before any
other step and ask the developer to `/clear`, `/model opus`, `/effort high`, then re-run.
Never switch model mid-session yourself. Effort comes from this command's frontmatter.

Read `workflows/port-feature.md` and follow it exactly for the arguments above. 
Before touching any repo, read its `context/repos/<name>.md` (and the repo's own
`AGENTS.md`/`CLAUDE.md` if present). AGENTS.md guardrails apply throughout.
