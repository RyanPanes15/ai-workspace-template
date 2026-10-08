---
title: <one line — the mistake, stated as what went wrong>
triggers: [<symptoms, task types, or words in a request that mean this file applies>]
applies_to: [<workflows / repos / areas — e.g. analyze, fix, review-pr, any>]
severity: <high = shipped a defect or cost a revert · medium = cost a rework round · low = wasted time>
status: active            # active | retired (cause removed — say how)
first_seen: <YYYY-MM-DD>
last_seen: <YYYY-MM-DD>
occurrences: 0
---

## The mistake
<What the agent did, in general terms. One short paragraph.>

## Why it happens
<The reasoning shortcut or missing check that makes it likely.>

## Rule
<What to do instead — imperative, checkable. One to three bullets.>

## Check before you finish
<The concrete test that proves you did not repeat it (a command, an assertion, a line in the report).>

## Occurrences
<!-- newest first; one line each; keep ≤ 10 lines, then summarise older ones as a count -->
<!-- - YYYY-MM-DD · <item/task> · <what happened> · <cost: rework / revert / wasted round> -->

## Related
<!-- other mistakes/ files, AGENTS.md sections, workflow steps -->
