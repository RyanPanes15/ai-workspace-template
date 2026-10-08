---
description: Cluster log errors into distinct issues with stable fingerprints and classify each NEW / STILL OPEN / FIXED IN CODE / WHITELISTED against current code. Read-only.
argument-hint: "[--since YYYY-MM-DD] [--channel server|client] [log glob]"
allowed-tools: Read, Grep, Glob, Write, Bash(python modules/log-triage/triage_logs.py:*), Bash(node modules/log-triage/symbolicate.js:*), Bash(python modules/area-index/area_index.py:*), Bash(git fetch:*), Bash(git log:*), Bash(git show:*), Bash(git tag:*), Bash(git branch:*), Bash(git rev-parse:*), Bash(python modules/code-slice/cs.py:*)
model: sonnet
effort: medium
---

# /log-triage

Arguments: `$ARGUMENTS`

Read `workflows/log-triage.md` and follow it exactly. Time matters here: do not spend
time that can be avoided; work the highest-count issues first.
