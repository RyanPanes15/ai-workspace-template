---
title: A large file was left truncated after an edit
triggers: [post-edit check failed, SyntaxError at end of file, unexpected EOF, file shorter than expected]
applies_to: [any]
severity: medium
status: active
first_seen:
last_seen:
occurrences: 0
---

## The mistake
An edit on a large file reported success but the file ended mid-statement; the failure
surfaced later, far from the edit.

## Why it happens
Edit/Write on very large files can truncate; success output is not proof of content.

## Rule
- When `post_edit_check.py` fails, stop and re-read the **whole** file, then repair it.
- For files over ~50 KB, prefer small anchored edits over rewriting the file.

## Check before you finish
`python .claude/hooks/post_edit_check.py <files you edited>` reports 0 failures.

## Occurrences

## Related
.claude/hooks/post_edit_check.py · docs/lessons-catalog.md L33
