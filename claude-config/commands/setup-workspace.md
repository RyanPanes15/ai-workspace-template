---
description: Register the project's frontend, backend and additional context repos and generate the workspace map (wraps setup/setup_workspace.py).
argument-hint: "[--check | --render | add <role>]"
allowed-tools: Read, Write, AskUserQuestion, Bash(python setup/setup_workspace.py:*), Bash(py setup/setup_workspace.py:*), Bash(git clone:*)
effort: medium
---

# /setup-workspace

Arguments: `$ARGUMENTS`

Follow `.claude/skills/setup-workspace/SKILL.md`. Always list the repo roles and why
each helps before asking for them; confirm before cloning or writing.
