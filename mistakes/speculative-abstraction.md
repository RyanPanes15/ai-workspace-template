---
title: Built abstractions, options or layers nobody asked for
triggers: [new project, new module, "make it flexible", generic, framework, plugin, config option, base class, factory]
applies_to: [build, scaffold-project, implement-change]
severity: medium
status: active
first_seen:
last_seen:
occurrences: 0
---

## The mistake
Added an interface, base class, plugin point, config flag or generic helper with a
single user "for later" — more code to read, test and change, with no second use.

## Why it happens
On a blank page every future need looks likely; abstraction feels like quality.

## Rule
- YAGNI: build for the acceptance criteria in the spec, nothing more.
- Introduce an abstraction only when a second real use exists (or a test seam needs it).
- Open/closed only where the same kind of change has already happened twice.

## Check before you finish
For every new interface / option / helper in the diff, name its second caller or the
criterion that needs it; delete the ones you can't.

## Occurrences

## Related
docs/design-principles.md (5, 7, 8, 10) · workflows/build.md Step 4
