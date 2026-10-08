---
description: Analyze one or more work items end-to-end without code changes (precondition trace, new-code hypothesis, conditional reference comparison, sweep pre-flag).
argument-hint: "<id> | <id,id,...>"
allowed-tools: Read, Grep, Glob, Task, Write, Bash(python modules/area-index/area_index.py:*), Bash(python modules/payload-decode/decode_response.py:*), Bash(git log:*), Bash(git blame:*), Bash(git show:*), Bash(git rev-list:*), Bash(python modules/tracker/fetch_items.py:*), Bash(python modules/db-query/run_query.py:*), Bash(python modules/code-slice/cs.py:*)
effort: high
---

# /analyze

Arguments: `$ARGUMENTS`

**Tier gate (deep).** If this session was not started as a deep session — the model
you are running as is not opus-class (`CLAUDE.md` §Session shapes) — stop before any
other step and ask the developer to `/clear`, `/model opus`, `/effort high`, then re-run.
Never switch model mid-session yourself. Effort comes from this command's frontmatter.

Read `workflows/analyze.md` and follow it exactly for the arguments above. 
Before touching any repo, read its `context/repos/<name>.md` (and the repo's own
`AGENTS.md`/`CLAUDE.md` if present). AGENTS.md guardrails apply throughout.
