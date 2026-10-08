# Design principles — constraints, not a checklist

Apply to code you **write** (new features, ports, change requests, and the code a fix
adds). Do not refactor existing code to these principles unless the change needs it
(see "Structural change" below). When two principles collide, pick the one that cuts
future cost **in this codebase** — its conventions, its team, its change history.
Violate a slogan when judgment says so, and say why in the report.

1. **Separation of concerns** — one kind of work per part (UI / domain / persistence /
   infrastructure). The root principle; most others follow from it.
2. **Encapsulation / information hiding** — a small, stable contract; internals stay
   internal.
3. **High cohesion, loose coupling** — what changes together lives together;
   independent parts talk through narrow interfaces.
4. **DRY — of knowledge, not of lines.** One authoritative representation of each
   rule, constant or mapping. Two similar-looking blocks that change for different
   reasons are not duplication; merging them is over-DRY and couples them.
5. **KISS** — the simplest design that works; complexity is a long-term tax.
6. **Single responsibility** — one reason to change.
7. **Depend on abstractions** — policy does not depend on details; both depend on a
   contract. Only where a second implementation or a test seam actually exists.
8. **YAGNI** — no speculative features, frameworks, options or "later" hooks.
9. **Composition over inheritance** — assemble pieces; avoid growing hierarchies.
10. **Open/closed, with discipline** — extend at stable boundaries, and only where the
    same kind of change has already happened twice.

Also: Law of Demeter (talk to direct collaborators) · fail fast and make illegal states
unrepresentable (validate at the boundary, types over runtime checks) · optimize for
deletion (easy to remove beats easy to extend) · do one thing and compose.

## Structural change ("tidy first")

If a change genuinely needs the code restructured first:
1. Make the restructure a **separate commit that changes no behavior** — tests and
   observable output identical before and after (state how you checked).
2. Then the behavior change, in its own commit.
3. Only with the developer's consent when the restructure goes beyond the files the
   change already touches — otherwise it is scope creep (`workflows/fix.md` Step 5.4).

## Simplicity pass (non-trivial changes)

Before the reviewer round, ask once: *knowing everything learned so far, is there a
simpler or cleaner change at the right layer?* Signs to look for: a special case that
a better condition would remove, a fix in the caller that belongs in the callee (or
the reverse), a new flag where existing state already answers the question, logic
duplicated from somewhere that should be reused. Skip the pass for obvious one-line
fixes — don't over-engineer them.

## Comments

- Comment only where the code is not self-explanatory. Most lines need none.
- A comment says **what the code does**, in one short line.
- **Never** a comment about what something is for, why it exists, its history, a
  ticket/item ID, or who changed it — that belongs in the commit message and PR.
- No commented-out code, no restating the line below, no banner/section comments.
- Docstrings: one line stating what the function does; add parameters/returns only
  when the signature does not make them clear.
- **Ports are the exception.** When code is migrated from the reference
  implementation, carry the reference's comments over as they are, on the equivalent
  new code — including ones that explain purpose or history — so the port can be
  compared against the original line by line. Translate only if the team's language
  rule requires it, and keep the original text alongside. The rules above apply only
  to comments on code or features that the reference does not have (new validation,
  new helpers, deliberate changes).
- This rule overrides a file's existing comment density: do not add comments to match
  a heavily commented file, and do not strip existing comments you did not touch.
