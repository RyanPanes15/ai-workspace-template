# Parity baseline — ported behavior that must not break

Features on an existing port change some behavior on purpose; everything else must
keep matching the reference. List the behavior that guards the port and how it is
checked, so every feature's regression pass runs the same checks.

| area | behavior that must hold | how to check (test / script / manual steps) | last verified |
| --- | --- | --- | --- |

## Shared components with many consumers
<!-- component → consumer count → regression check; touching one means checking all -->

## Known intentional divergences
<!-- feature → what changed vs the reference → spec link -->
