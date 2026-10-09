---
name: setup-workspace
description: Bootstrap or update this agent workspace for a project — collect the frontend, backend and additional context repos (database, reports, docs, tests, legacy/reference, infra), clone or link them, and generate workspace.config.json, the AGENTS.md workspace map, and per-repo context files. Use when the workspace is new, when a repo is added/removed, or when asked to "set up the workspace".
---

# Setup workspace

Drives `setup/setup_workspace.py` conversationally. The script does the writing;
you collect answers, confirm, and run it non-interactively.

## 1. Check current state
- `python setup/setup_workspace.py --check` (exit 1 = missing repos, or no config yet).
- Read `workspace.config.json` if present — you are updating, not starting over.

## 2. Ask the project, then its type
The workspace can hold several projects (`projects[]` in the config); each repo belongs
to one or more projects, and a project may name other projects' repos as
`reference_repos` (e.g. the app a port is ported from). Ask whether this is a new project
or an update to an existing one, then ask which of the four types it is (several
allowed) — it decides which repo roles are
required, which context files get scaffolded and which modules are on
(`docs/project-types.md`):
1. **greenfield** — fresh new code project (repos may not exist yet: offer to create them)
2. **maintenance** — bug-fix work on released software
3. **port** — migration from a reference system (legacy repos are required)
4. **feature** — feature additions on an existing port
Put the answer in the answers file as
`"projects": [{"name", "description", "types": [...], "repos": [...], "reference_repos": [...]}]`
— keep the existing projects in the file. A project's reference repos satisfy the port
type's legacy-repo requirement. To change one project's type:
`python setup/setup_workspace.py --set-type <types> --project <name>`.

## 2b. Tell the user what you need (always, before asking)
Send one message listing the roles and why each helps:

| Role | Why agents need it | Without it |
| --- | --- | --- |
| **Frontend** (required-ish) | UI screens, forms, client state | UI items analyzed only from reports/API |
| **Backend** (required-ish) | endpoints, validation schemas, business logic, SQL | no cross-layer verification |
| Database / schema | column widths, nullability, constraints | live DB or snapshot only |
| Reports | report templates/generation | report defects traced only to API data |
| Docs / specs | authoritative specs, curated knowledge (read first) | reverse-engineering code |
| Tests / QA | E2E suites, test data, QA knowledge | app repos' own harness only |
| Legacy / reference (client, server, schema) | de-facto spec for port/parity defects | no Tier-2 regression analysis |
| Infra / CI | pipelines, env config | env defects need manual context |

Skip roles the type doesn't use (greenfield has no legacy repos) and mark the ones it
requires. For a greenfield repo that doesn't exist yet, set `"create": true` with a
local path. For each repo ask: git URL **or** local path · short name · policy
(`editable` / `pr-only` / `flag-only` / `read-only`; defaults: app repos editable,
reports flag-only, docs pr-only, everything else read-only) · integration branch for
editable repos. Also ask project name, one-line description, ticket language,
stakeholder-reply language, work modes, branch/commit/PR naming, and which optional
modules to enable (tracker fetcher, DB query wrapper, usage ledger) plus tracker
sources (type, location, ID prefix).

Use AskUserQuestion for the choices; free-text for URLs/paths. Don't guess a repo URL.

## 3. Confirm, then run
1. Write the answers to `_work/setup-answers.json` (shape: `workspace.config.example.json`).
   `--config` replaces the whole config: when adding a project, start from the current
   `workspace.config.json` and add to it.
2. Show the user the repo table you are about to register and any clones that will run.
3. On confirmation: `python setup/setup_workspace.py --config _work/setup-answers.json --yes`
   (use `--dry-run` first if the user wants a preview).
4. Relay the script's summary — especially roles **not provided** and what agents
   will fall back to — and the next steps.

## 4. After setup
- Open each new `context/repos/<name>.md` with the user and fill structure,
  ownership, and known defect patterns from the repo's README / own AGENTS.md.
- **Reconcile the repo's own agent files** (`AGENTS.md`, `CLAUDE.md`, `.cursorrules`,
  …; the stub lists them under Tech stack). Classify each section:
  - *repo-specific* (build quirks, special test commands, paths to avoid, legacy
    traps) → copy into `context/repos/<name>.md`;
  - *duplicate* of a workspace rule, whatever the wording → note it, nothing to copy;
  - *conflict* — same topic, different substance, or a workspace rule that doesn't fit
    this stack → stop and ask the user; record the decision under "Own agent files"
    in `context/repos/<name>.md`. A conflict with an AGENTS.md §3 guardrail keeps the
    guardrail unless the user carves out an exception;
  - *cross-cutting* (a pattern other repos would follow) → note it as a
    `/maintain-context` promotion candidate;
  - *decorative or stale* → ignore.
  Never edit the repo's own files; propose changes for the user to make as a PR under
  the repo's policy.
- Check the workspace still fits the new stack: its quiet commands run, and
  `.claude/hooks/post_edit_check.py` covers its file types.
- If usage metrics were enabled, remind them to restart and verify a ledger line.
- Never write credentials into config — they go in `secrets/` by the user.
- Adding a repo later: update the config (or re-run interactively), then
  `python setup/setup_workspace.py --render`.
