---
title: A port silently dropped or weakened a rule the reference enforced
triggers: [port, migrate, rewrite screen, legacy, reference, parity, "same as old system", inventory]
applies_to: [port-feature, fix, review-pr]
severity: high
status: active
first_seen:
last_seen:
occurrences: 0
---

## The mistake
The ported screen looked right, but a rule that "didn't look like logic" was lost: an
onChange that updated another field, a default that depended on role or date, a
server-side check in a persister, a byte-length limit ported as characters, an error
message the reference showed that the port swallows.

## Why it happens
Porting follows the visible form; rules hidden in handlers, converters and SQL are
skipped when there is no written inventory to check against.

## Rule
- Inventory every rule with its reference file:line **before** generating code.
- Check equivalence, not presence (limits in bytes, required-ness, defaults, ranges).
- Integrity rules must exist on the server; error paths must stay visible.

## Check before you finish
`completeness-verifier` returns no MISSING / WEAKENED / LAYER GAP, and the area's row in
`context/port-map.csv` points at the inventory file (`port_status.py --check` passes).

## Occurrences

## Related
workflows/port-feature.md · .claude/agents/completeness-verifier.md
