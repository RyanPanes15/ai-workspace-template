# CLAUDE.md

The canonical instructions for this workspace live in `AGENTS.md` so every model and
tool reads the same contract. Claude Code imports it here:

@AGENTS.md

## Claude Code specifics

- Slash commands in `.claude/commands/` are thin wrappers around `workflows/*.md`;
  their frontmatter pins model tier and effort (catalog: `.claude/model-routing.md`).
- Subagents in `.claude/agents/`: `item-scaffolder` (light), `report-formatter`
  (light), `fix-verifier` (deep), `completeness-verifier` (deep).
- Hooks: `.claude/hooks/safe_git_allow.py` auto-allows only the safe git shapes of
  the PR workflow; everything else falls through to the normal permission prompt.
  `repo_guard.py` blocks edits/mutating git in read-only repos; `post_edit_check.py`
  syntax-checks each edited file and reports failures back (exit 2).
  Optional: `modules/usage-metrics` Stop hook (enabled by setup).
- `ultrathink` deepens a single turn; switching to a higher tier is a manual,
  per-invocation decision (`/model`), never a default.
- `mistakes/`: one file per class of mistake; read `mistakes/INDEX.md` before work and
  update/add a file whenever a mistake is caught (AGENTS.md §10).
- Machine-local notes go in `AGENTS.local.md` / `CLAUDE.local.md` (both gitignored).
