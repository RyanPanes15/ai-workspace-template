# {{name}} — {{role_label}}

**Policy:** {{policy}} · **Path:** `{{path}}` · **Remote:** {{remote}}
**Integration branch:** {{integration_branch}} · **Protected:** {{protected_branches}}

> Read before searching, editing, or running git here. Inherits AGENTS.md.
> Auto-detected facts are marked (detected) — confirm them.

## Tech stack
{{detected_stack}}

## Commands
{{detected_commands}}

## Quiet commands
<!-- Failures-only invocations. Agents run these through the `test-runner` subagent so
     only failures and counts enter the conversation; full output rides along on every
     later request otherwise. Confirm each flag once. -->
{{quiet_commands}}

## Structure — where things live
<!-- e.g. pages/ forms/ stores/ models/ routes/ services/ persisters/; the ID → file
     mapping rule (how an area/screen ID maps to files). -->

## Ownership — which items belong here
<!-- e.g. UI rendering, form state, client validation → here; data/logic → backend. -->

## Common defect patterns in this repo
<!-- Add as they are found: symptom → mechanism → check. One worked example each. -->

## Own agent files — conflicts with workspace rules
<!-- Only when the repo ships AGENTS.md / CLAUDE.md / .cursorrules: each conflict with a
     workspace rule and the decision (workspace rule wins / scoped exception), dated. -->

## Before submitting a change
- Verification could have failed (pre-fix control reproduced the symptom).
- Lint + typecheck + tests actually ran on the changed files.
- Production build passes when the bundler transforms code.
- Shared components: every consumer checked (horizontal sweep).
- New code follows `docs/design-principles.md`; comments only where needed, one short
  line on what the code does.
- Prefer a local guard over editing a shared component; a shared-component change is
  its own task with its own sweep and regression pass.

## Pre-push / post-PR
- Pre-push: `git pull origin {{integration_branch}}`, then the lint gate.
- Post-PR: `git checkout {{integration_branch}}`.
