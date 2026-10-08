---
title: Trusted a lint / test / typecheck "pass" that checked nothing
triggers: [lint passed, tests green, tsc clean, 0 errors, checkstyle, CI green]
applies_to: [fix, implement-change, port-feature]
severity: medium
status: active
first_seen:
last_seen:
occurrences: 0
---

## The mistake
Reported a clean gate when the tool had linted zero files (wrong branch argument, empty
diff), fetched-and-exited, or had its error count hidden by truncated output.

## Why it happens
A zero exit code and no visible errors look identical to a real pass.

## Rule
- Confirm the tool ran on the intended files (file count > 0, report rewritten).
- Read full output, not a `tail`; pass the feature branch to diff-based gates.
- Prefer `modules/lint-gate`, which fails on the vacuous cases.

## Check before you finish
The report states how many files each gate checked.

## Occurrences

## Related
docs/git-workflow.md 10.5.1 · modules/lint-gate
