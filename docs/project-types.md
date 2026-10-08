# Project types

The template runs four kinds of project. Setup asks which one (a project can be more
than one — e.g. a port that is also taking feature requests) and then:
writes the matching rules into AGENTS.md (§2 *Active project profile*), scaffolds the
context files that type needs, enables its default modules, and warns about repo roles
it needs but you didn't register. Change it later with
`python setup/setup_workspace.py --set-type port,feature`.

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

## Moving between types

Projects change type over their life: a port becomes maintenance after go-live, and a
maintained port starts taking features. Add the new type rather than replacing the
old one while both kinds of work run (`--set-type port,feature`); drop the old one when
its work is finished. Scaffolds are only ever added, never overwritten.

## Where each type's rules live

- `profiles/<type>/profile.json` — machine-readable defaults (mode, truth order,
  required/recommended repo roles, modules, primary commands, scaffold list).
- `profiles/<type>/AGENTS.profile.md` — the rules inserted into AGENTS.md §2.
- `profiles/<type>/scaffold/` and `profiles/_shared/scaffold/` — files copied into
  `context/` and `docs/` on setup (never overwriting).

Edit the profile files to tune a type for your organisation; re-run
`python setup/setup_workspace.py --render` to apply.
