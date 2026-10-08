# Workflow: Scaffold a new project (greenfield bootstrap)

**Mode:** build. **Tier:** deep @ high. Run once per new repo, after
`context/architecture.md` has a confirmed first draft.

1. **Plan.** `_work/runs/scaffold/TASKS.md`. Confirm with the developer: stack, package
   manager, runtime versions, repo names, hosting, CI provider. These are decisions —
   ask, don't assume.
2. **Record the stack** as ADR 0001 (`docs/adr/0001-stack.md`, status proposed →
   accepted by the developer).
3. **Create the repo skeleton** (repos registered by setup; create missing ones with
   `setup_workspace.py` `"create": true`). Minimum per repo:
   - README (run, test, build), `.gitignore`, `.editorconfig`, `.gitattributes`
   - formatter + linter config and a `lint` / `lint:fix` script
   - type checking where the language has it, in strict mode
   - a test runner with one passing test and the `test` script
   - environment config with an `.env.example` (no secrets) and validation at startup
   - folder layout from `context/conventions.md`
   - CI workflow: install → lint → typecheck → test → build on every PR
4. **Wire cross-cutting basics** named in `context/architecture.md`: error handling and
   mapping, logging with request IDs, health endpoint, config loading. Nothing
   speculative (YAGNI) — no feature flags, plugin systems or abstractions without a
   second user.
5. **Verify** the skeleton: every script runs clean locally; CI config is valid; the
   app starts and the health check answers.
6. **Register** the repo details: `python setup/setup_workspace.py --render`, then fill
   `context/repos/<name>.md` (commands, layout, ownership) and `context/conventions.md`.
7. **Overview page.** Create `<repo>/README.html` with `workflows/repo-overview.md`
   (general details, scope, tech stack, architecture, file structure, process flows).
   Facts not decided yet are written as "Not yet defined".
8. **Report** — what I need from you (accept ADR 0001, create the remote, CI secrets,
   facts the overview marked "Not yet defined") → what was created → how to run it.
   Creating remotes and pushing need explicit consent.
