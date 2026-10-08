---
title: Closed a hypothesis on a trial that never actually executed
triggers: [didn't reproduce, no error, nothing happened, click had no effect, passed on first try]
applies_to: [analyze, fix, review-pr, verification]
severity: high
status: active
first_seen:
last_seen:
occurrences: 0
---

## The mistake
Reported "tried it — not reproducible" (or "fix verified") when the action never ran:
disabled button, form not dirty, synthetic click with no real event, coordinate miss,
wrong input path, field state that disarmed the code path.

## Why it happens
"No error" reads like success; the missing side effect goes unnoticed.

## Rule
- Assert the trial executed: request in network/server log, row written, handler entered.
- "No error **and no write**" = invalid trial, not a pass.
- Drive every input path that can commit the value; satisfy the guard that arms the path.

## Check before you finish
Each trial in the report names its proof of execution; the pre-fix control reproduced
the symptom.

## Occurrences

## Related
docs/verification-guide.md §4, §5.2 · workflows/fix.md Step 9.5
