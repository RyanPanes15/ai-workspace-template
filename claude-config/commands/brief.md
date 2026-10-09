---
description: Turn a rough request into a brief — extract task, target command, repo scope, context and binary acceptance criteria (≤3 questions, after inferring from the workspace), write _work/runs/<task>/BRIEF.md and name the command to run.
argument-hint: "<rough request | tracker id | spec path>"
allowed-tools: Read, Grep, Glob, Write
effort: medium
---

# /brief

Arguments: `$ARGUMENTS`

Read `workflows/brief.md` and follow it exactly for the arguments above. Write only
`_work/runs/<task>/BRIEF.md`; open no repo. AGENTS.md guardrails apply throughout.
