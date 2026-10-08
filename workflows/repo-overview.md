# Workflow: Repo overview page (README.html)

**Mode:** build (documentation). **Tier:** standard @ medium.
**Input:** one repo name from the workspace map. Runs as step 7 of
`workflows/scaffold-project.md` for every new repo, and on demand (`/repo-overview <name>`)
after structural changes. **Output:** `README.html` at the repo root.

Only for `editable` repos. For `read-only` / `flag-only` / `pr-only` repos, stop and say
so — the page is part of the repo and goes through that repo's normal change path.

1. **Plan.** Add the steps to the active `TASKS.md` (or create
   `_work/runs/repo-overview-<name>/TASKS.md`). Pre-flight: `git -C <repo> branch
   --show-current` and `status -s`.
2. **Start from the template.** Copy `docs/templates/repo-readme.html` to
   `<repo>/README.html`. The template is the source of truth for the page shell
   (styles, theme toggle, floating buttons, zoomable diagrams) — change content, not
   the shell. If a `README.html` already exists, update its content in place and keep
   the shell from the template.
3. **Gather facts — every statement traces to a file read this session:**

   | Section | Sources |
   | --- | --- |
   | General details | `workspace.config.json` entry, `context/repos/<name>.md` |
   | Project scope | `context/architecture.md`, `docs/specs/`, the repo's `README.md` |
   | Tech stack | package manifests and lockfiles (versions from there, not memory) |
   | Architecture | entry points, `context/architecture.md`, accepted ADRs |
   | File structure | `python modules/code-slice/cs.py outline <repo>`; top two levels only |
   | Process flows | entry points + `cs.py flow file#Name` for each main flow |
   | Commands | manifest scripts / Makefile / task runner config |
   | Configuration | `.env.example` and the config schema — names and purpose only |
   | Testing & CI | test config, lint config, CI workflow files |
   | Conventions | `context/conventions.md`, lint/formatter config |
   | Related repos | AGENTS.md workspace map (ownership routing) |
   | Decisions | `docs/adr/`, `docs/specs/` |

   Unknown or not yet built → write "Not yet defined". Never invent a flow, version or
   owner. Delete a section only when it cannot apply to this repo's role.
4. **Fill the page.** Replace every `{{...}}` placeholder and `fill:` comment; add rows,
   flows and diagrams as needed. Process flows: one `h3` + 1–3 sentence summary +
   diagram per main flow (request lifecycle, auth, core transaction, background jobs,
   build/deploy — whichever exist).
5. **Diagram rules** (Mermaid):
   - Copy a whole `details.diagram` block from the template for each diagram.
   - Quote every node and edge label (`A["Step — detail"]`, `-->|"yes"|`).
   - No raw `<` or `>` inside labels except `<br/>`; no HTML comments inside
     `pre.mermaid`.
   - Keep a linear chain to about 5 nodes per row; split longer chains into
     `subgraph` rows (`direction LR`) linked by one edge, so the diagram stays readable
     at Fit.
6. **Secrets and attribution.** No values from `.env`, `secrets/`, `AGENTS.local.md` or
   deployed config; no personal names unless the workspace map lists them as owners.
7. **Verify.** Open the page in a browser (or render each `pre.mermaid` source with
   Mermaid) and confirm every diagram renders — no "Syntax error" boxes — and no
   `{{` placeholder remains (`grep -n "{{" <repo>/README.html` returns nothing). A page
   that was not rendered is not verified; say so in the report.
8. **Report** — what I need from you (facts marked "Not yet defined" that you can
   supply) → sections written → files changed. Committing follows the repo's normal
   change path; pushing needs explicit consent.
