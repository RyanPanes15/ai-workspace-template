# Project types

The template runs four kinds of project. Setup asks which one (a project can be more
than one — e.g. a port that is also taking feature requests) and then:
writes the matching rules into AGENTS.md (§2 *Active project profiles*), scaffolds the
context files that type needs into `context/projects/<project>/`, enables its default
modules, and warns about repo roles it needs but you didn't register. A workspace can
hold several projects, each with its own types. Change one later with
`python setup/setup_workspace.py --set-type port,feature --project <name>`.

| | 1. Fresh new code | 2. Maintenance (bug-fix) | 3. Port migration | 4. Feature on existing port |
| --- | --- | --- | --- | --- |
| Profile id | `greenfield` | `maintenance` | `port` | `feature` |
| Work mode | build | defect | port | change |
| "Correct" means | the spec + accepted ADRs | released behavior; verified report premise | reference behavior (parity) | the feature spec; port baseline must not break |
| Reference repos | none | optional | **required** (legacy client/server) | optional (untouched behavior only) |
| Main workflows | scaffold-project, build, review-pr | analyze, fix, log-triage, db-query, stakeholder-reply, area-loop | port-feature, analyze/fix for regressions | change-request, build (net-new), fix |
| Scaffolded context | architecture, conventions, ADRs, spec template | environment, test records, glossary, spec-changes | port-map.csv, port-conventions, environment, glossary, spec-changes | parity-baseline, spec template, environment, glossary, test records |
| Default modules | usage-metrics, pr-metrics | tracker, db-query, usage, log-triage | tracker, db-query, usage, pr-metrics, port-status | tracker, db-query, usage, pr-metrics |
| Mistake files always read | speculative-abstraction | static-read-of-runtime-bug, wrong-environment-evidence, invalid-negative-trial | dropped-reference-rule, name-keyed-sweep | speculative-abstraction, name-keyed-sweep |
| Comments | short-comment rule | short-comment rule | reference comments carried over as they are; rule only for new code | ported code keeps its comments; new code follows the rule |
| Typical gate | spec confirmed before build; ADR for costly decisions | reviewer round with pre-fix control | completeness verifier: no MISSING/WEAKENED/LAYER GAP | regression of every touched shared component |

## Work modes (what "correct" means)

Every workflow states which mode it runs in; AGENTS.md §2 carries the one-line form.

- **Build mode** (fresh code): the spec's acceptance criteria and accepted ADRs define
  correct. There is no reference to match; unclear requirements go back to the
  requester, costly decisions get an ADR.
- **Defect mode** (bug fixing): the reference implementation / prior behavior is the
  de-facto spec. A difference from it is a *regression hypothesis*, not a verdict —
  first check whether it was an intentionally requested change (a spec-change
  registry, changelog, or ticket history).
- **Port mode** (migration): parity with the reference is the spec, re-derived in the
  target stack's idiom. Inventory the reference's rules before writing code; carry its
  comments over; requested changes are recorded, never assumed.
- **Change mode** (feature / change request): the request text is the spec. The
  deliberate divergence *is* the deliverable; the reference only defines what must
  not break. Ambiguity goes back to the requester — don't resolve it by guessing.
  A bug found in delivered change work is handled in defect mode.

## Moving between types

Projects change type over their life: a port becomes maintenance after go-live, and a
maintained port starts taking features. Add the new type rather than replacing the
old one while both kinds of work run (`--set-type port,feature --project <name>`); drop the old one when
its work is finished. Scaffolds are only ever added, never overwritten.

## Where each type's rules live

- `profiles/<type>/profile.json` — machine-readable defaults (mode, truth order,
  required/recommended repo roles, modules, primary commands, scaffold list).
- `profiles/<type>/AGENTS.profile.md` — the rules inserted into AGENTS.md §2.
- `profiles/<type>/scaffold/` and `profiles/_shared/scaffold/` — files copied into
  `context/` and `docs/` on setup (never overwriting).

Edit the profile files to tune a type for your organisation; re-run
`python setup/setup_workspace.py --render` to apply.
