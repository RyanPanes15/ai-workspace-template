---
description: Draft an architecture decision record (status proposed) for a decision that is costly to reverse.
argument-hint: "<decision title>"
allowed-tools: Read, Write, Grep, Glob
model: sonnet
effort: medium
---

# /adr

Arguments: `$ARGUMENTS`

Create `docs/adr/NNNN-<slug>.md` from `docs/adr/0000-template.md` with the next free
number. Fill Context, Decision, Alternatives considered (at least two, with why not) and
Consequences from the conversation and `context/architecture.md`. Status stays
*proposed* — the team accepts it. If a prior ADR is affected, link it and say whether it
would be superseded.
