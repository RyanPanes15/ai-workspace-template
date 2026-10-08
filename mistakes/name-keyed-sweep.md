---
title: Horizontal sweep keyed on identifiers missed the same defect under other names
triggers: [yokoten, 横展開, horizontal sweep, "same bug elsewhere", sibling screens, "fixed everywhere"]
applies_to: [fix, review-pr, port-feature]
severity: high
status: active
first_seen:
last_seen:
occurrences: 0
---

## The mistake
Searched for the fixed field/function name (or a naming glob), reported "no other
sites", and the same defect class later shipped again from a sibling that used a
different name.

## Why it happens
Identifiers are the easiest grep key; the defect's shape is harder to express.

## Rule
- State the defect class in one sentence with **zero identifiers**, then search by roles/shape.
- Run the same detector on a known-good sibling (control) before trusting hits.
- Open every candidate before listing or dismissing it.

## Check before you finish
The sweep section shows the zero-identifier sentence, the structural search terms, the
control result, and a verdict per candidate.

## Occurrences

## Related
AGENTS.md §5 · workflows/fix.md Step 7
