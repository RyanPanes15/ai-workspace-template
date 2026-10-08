---
title: Presented a static code read as the root cause of a runtime-state bug
triggers: [disabled/enabled, blank on load, stale value, toggle not registering, race, slow render, empty dropdown, "doesn't update"]
applies_to: [analyze, fix, review-pr]
severity: high
status: active
first_seen:
last_seen:
occurrences: 0
---

## The mistake
Read the code, found a plausible mechanism, and reported it (or fixed it) as the cause
of a state/timing symptom without observing the running app. The fix shipped and had to
be reverted because the real cause was elsewhere.

## Why it happens
A clean-looking static path feels conclusive; running the screen costs effort.

## Rule
- A static read of a runtime-state symptom is a **hypothesis capped at medium**.
- MEDIUM → suggest a self-test; LOW → run it (`docs/verification-guide.md`) before editing.
- If runtime evidence is impossible, say "unverified — runtime evidence unavailable because X".

## Check before you finish
The report cites a runtime observation (screenshot value, console/log line, measured
timing) for the mechanism — or carries the "unverified" label.

## Occurrences

## Related
AGENTS.md §2 Evidence rules · workflows/analyze.md Step 7.3 · workflows/fix.md Step 4
