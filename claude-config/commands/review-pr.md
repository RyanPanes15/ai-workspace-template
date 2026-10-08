---
description: Review a pull request and report only merge-blocking problems, each with file:line, why it is wrong, and how to show it fails. Read-only; drafts the review comment.
argument-hint: "<PR number | URL | branch>"
allowed-tools: Read, Grep, Glob, Task, Bash(gh pr view:*), Bash(gh pr diff:*), Bash(gh pr checks:*), Bash(git fetch:*), Bash(git log:*), Bash(git show:*), Bash(git diff:*), Bash(git blame:*), Bash(python modules/area-index/area_index.py:*), Bash(python modules/lint-gate/lint_gate.py:*), Bash(python modules/code-slice/cs.py:*)
model: opus
effort: high
---

# /review-pr

Arguments: `$ARGUMENTS`

Read `workflows/review-pr.md` and follow it exactly. Never post the review; the
developer does.
