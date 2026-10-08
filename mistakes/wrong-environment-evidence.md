---
title: Drew a conclusion from the wrong database / log environment / tenant / build
triggers: [row not found, "no data since", can't find reporter's record, works for me, different result than tester]
applies_to: [analyze, db-query, fix, log-triage]
severity: high
status: active
first_seen:
last_seen:
occurrences: 0
---

## The mistake
Queried or observed one environment while the report came from another, then stated
(and later retracted) a root cause — "no rows exist", "not reproducible", "fixed".

## Why it happens
Config silently points somewhere else; instance names look identical; the switch
happened mid-session.

## Rule
- Name the environment (DB instance, log env, tenant, build) on every observation.
- Discriminate instances by **data** (the reporter's own record, `COUNT(*)`+`MAX(pk)`),
  not by a name that can be identical.
- Absence of a row is not evidence until the instance is confirmed.

## Check before you finish
Every evidence line in the report carries its environment label, and the reporter's
own record was found on the instance you used.

## Occurrences

## Related
AGENTS.md §2 · workflows/db-query.md "Before any SQL"
