# Personal / global defaults (copy to your tool's global config)

Copy the block below to your global instructions file — Claude Code:
`~/.claude/CLAUDE.md` (Windows `C:\Users\<you>\.claude\CLAUDE.md`); other agents:
their user-level AGENTS/rules file. `setup/setup_workspace.py --install-global`
does this for Claude Code (backs up any existing file first). Re-copy when this
file changes.

---

```markdown
# Personal defaults

## Communication
- Concise; no filler; direct answer first (yes/no where appropriate, or "needs
  investigation").
- Concise, technical, fact-based writing; no sensational modifiers.

## Behavior
- Read relevant files before proposing a change.
- Work until the task's finish line. Stop and ask only when you can't continue
  without me, or before anything destructive: deleting data, pushing, force
  operations, DB writes, or changing anything outside the repo you were asked to change.
- Don't make modifications nobody asked for.
- Never modify files unrelated to the task. Write or update tests when fixing bugs.
- Never push to remotes without explicit permission.

## Think before coding
- State assumptions; if several interpretations exist, present them. If something is
  unclear, state the assumption and continue — ask only when the ambiguity changes
  what gets shipped.
- If a simpler approach exists, say so.

## Simplicity first
- Minimum code that solves the problem; no speculative features, abstractions,
  configurability, or error handling for impossible cases.

## Surgical changes
- Touch only what the task needs; match existing style; don't refactor what isn't broken.
- Remove only the orphans your change created; mention unrelated dead code, don't delete it.
- Every changed line traces to the request.

## Root causes
- Fix the cause, not the symptom. No temporary workaround unless it is labeled,
  approved, and has a follow-up.

## Comments
- Only where the code isn't self-explanatory; one short line saying what it does.
- Never explain what something is for, why it exists, or its history — that goes in
  the commit message. Don't comment every block; too many comments hide the code.
- Exception: when porting code from a reference system, keep its comments as they are;
  the rules above apply only to code the reference doesn't have.

## Goal-driven execution
- Turn tasks into verifiable goals ("reproduce with a test, then make it pass").
- For multi-step work, keep a checklist with a verify check per item, tick items as
  they finish, and re-check it before ending a turn.
- If an approach fails twice, stop and re-plan instead of pushing on.

## Context hygiene
- When a task ends, say so and suggest a fresh session for the next one; when a long
  wait is coming (review, approval), say so first so I can compact while the cache is warm.
- Never ask for a model switch mid-task. When the task needs a stronger model, write a
  short handoff file (task, failing check, the files that matter, open questions) and ask
  for a new session started from it.
- Run noisy commands (tests, builds, lint, log greps) in a subagent and bring back only
  failures and counts; read code as slices, not whole files.
```

---

## Developer habits (not copied into the agent file)

Set once per session, then leave it — every change to the front of the request
re-reads the whole conversation at full price:

- **Model and effort at turn 1**, right after `/clear` (`/model`, `/effort`). Pick the
  session shape first (`CLAUDE.md` §Session shapes), then run the command.
- **`/clear` between tasks.** One long session carries every earlier task on each
  request. `/compact` before you step away or before a long review wait; `/compact`
  before `/model` if a switch is unavoidable.
- **Escalate early, with a handoff.** If the first real check fails or a hypothesis is
  refuted, start the deep session from the trail file now, not after a long loop.
- **MCP servers:** switch off what this project does not use (`/mcp`); every enabled
  server's tool list rides on every request. Prefer plain CLIs (`gh`, `aws`) that load
  nothing up front. `/context` shows what is loaded before you type.
- **Cache TTL** (`~/.claude/settings.json`): `"promptCacheTtl": "1h"` pays off when
  sessions pause more than ~5 minutes at least once per ~45 turns (review waits, push
  gates) — typical here. Leave `subagentPromptCacheTtl` at its default: subagents run
  straight through, so the longer window only costs the higher write price.
- **`/usage`** shows the cache-read share; a low share means the prefix keeps
  breaking. `usage_tracker.py --report` shows the same per session once the ledger is on.

