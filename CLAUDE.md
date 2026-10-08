# CLAUDE.md

The canonical instructions for this workspace live in `AGENTS.md` so every model and
tool reads the same contract. Claude Code imports it here:

@AGENTS.md

## Claude Code specifics

- Slash commands in `.claude/commands/` are thin wrappers around `workflows/*.md`;
  their frontmatter pins effort only. The model comes from the **session shape**
  below (catalog: `.claude/model-routing.md`).
- Subagents in `.claude/agents/`: `item-scaffolder` (light), `report-formatter`
  (light), `test-runner` (light), `fix-verifier` (deep), `completeness-verifier` (deep).
  Each has its own context and cache; the parent's cache is untouched.
- Hooks: `.claude/hooks/safe_git_allow.py` auto-allows only the safe git shapes of
  the PR workflow; everything else falls through to the normal permission prompt.
  `repo_guard.py` blocks edits/mutating git in read-only repos; `post_edit_check.py`
  syntax-checks each edited file and reports failures back (exit 2).
  Optional: `modules/usage-metrics` Stop hook (enabled by setup).
- `mistakes/`: one file per class of mistake; read `mistakes/INDEX.md` before work and
  update/add a file whenever a mistake is caught (AGENTS.md §10).
- Machine-local notes go in `AGENTS.local.md` / `CLAUDE.local.md` (both gitignored).

## Session shapes (cache discipline)

Every request re-sends the whole conversation; the cache is per model and breaks from
the first changed token. Model and effort are therefore chosen **once, at turn 1**, and
a session has one shape:

| Shape | Model · effort | Runs | Start with |
| --- | --- | --- | --- |
| **Deep** | opus · high | `/analyze`, `/fix`, `/review-pr`, `/port-feature`, `/implement-change`, `/build`, `/scaffold-project`, `/area-loop`, `/maintain-context` | `/clear` → `/model opus` → `/effort high` → the command |
| **Triage** (default floor in `settings.json`) | sonnet · medium | `/log-triage`, `/db-query`, `/stakeholder-reply`, `/adr`, `/repo-overview`, `/export`, ad-hoc questions | `/clear` → `/model sonnet` → `/effort medium` → the command |

`/clear` empties the conversation; it is not documented to reset the model, so set the
shape explicitly after it (the status line shows the current model). Press `s` in the
`/model` picker to apply the choice to this session only; a saved choice is outranked
by this project's `settings.json` at the next startup anyway.

Rules the agent follows:
- A deep command's **tier gate** checks the running model; wrong shape → stop and ask
  for `/clear` + `/model` + `/effort`, never switch model mid-session.
- **Escalate with a handoff, never with the transcript.** When a standard-tier task
  needs the deep tier (first refuted hypothesis, first failed real check, cross-repo +
  cross-layer), write the trail (`reports/<ID>-analysis.md`, or `_work/runs/<task>/HANDOFF.md`:
  task, failing check, the files that matter, open questions) and tell the developer to
  `/clear` and start a deep session from it.
- **One item per session by default.** The on-disk trail is the boundary between
  `/analyze` and `/fix`; `/area-loop` is the deliberate exception and carries its own
  budget and digest.
- Before a wait you expect to be long (review batch, push gate, "what I need from
  you"), say so, so the developer can `/compact` while the cache is warm. Before
  ending a task, suggest `/clear` for the next one.
- A hard moment inside a triage session: `ultrathink` deepens one turn. It rides in
  the user message, so it is likely cache-safe (unverified: check `/usage`). It is not a
  substitute for a deep session.
- Noisy output (tests, builds, lint, log greps) runs in `test-runner` or another
  subagent; only failures and counts come back. Use the **Quiet commands** section of
  `context/repos/<name>.md`.
