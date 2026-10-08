---
title: Read whole large files to find a few relevant lines
triggers: [large file, "read the file", stack trace, error log, reference screen, "how is X done on screen Y", PR review, DDL]
applies_to: [analyze, fix, port-feature, implement-change, review-pr, log-triage, db-query]
severity: medium
status: active
first_seen:
last_seen:
occurrences: 0
---

## The mistake
Opened a 2,000–9,000-line file (or several) to inspect one function, one field or one
stack frame. The context fills with unrelated code, later steps lose the details that
mattered, and the session runs out of budget before verification.

## Why it happens
Reading the whole file feels thorough, and the file path is already in hand.

## Rule
- Code: `modules/code-slice/cs.py` first (AGENTS.md §4 item 8). `show file:LINE` for a
  line, `trace` for a stack, `flow` for a process, `field --scope` for a reference
  screen, `diff` for review, `sql` for DB objects.
- Expand only what a slice folded and you need: `cs.py show file:a-b`.
- Whole-file reads only for files under ~300 lines, or when the task is the whole
  file (a rewrite, a full port inventory of that file).

## Check before you finish
Did any read in this task exceed ~300 lines? If so, was the whole file actually needed?

## Occurrences

## Related
AGENTS.md §4 · modules/code-slice/README.md
