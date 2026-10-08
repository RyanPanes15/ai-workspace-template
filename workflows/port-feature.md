# Workflow: Port a screen / feature from a reference implementation

**Tier:** deep @ high. **Input:** `<area-id>` (screen, module, endpoint) [`--audit-only`].
Use when rewriting from a legacy/reference system into the new stack.

## Stages (routing in brackets)
Keep `_work/runs/<area>/TASKS.md` with one line per stage and per inventory rule.
Track the area in `context/port-map.csv` (`python modules/port-status/port_status.py --add/--set`):
`inventoried` after stage 2, `in-progress` at stage 6, `verified` only when stage 7 passes
(with `--inventory` pointing at the inventory file).
0. Read `mistakes/INDEX.md`; open the files whose triggers match this port.
1. **Resolve & scope** — locate every reference file for the area (UI, layout,
   client logic, server handlers, persistence, SQL/stored procedures, messages).
   Read the context of each repo involved. [deep]
   Map the reference screen first: `cs.py outline <reference folder>`, then
   `cs.py field <field> --scope <reference screen> --show` per field — every place it is
   read, validated, saved or displayed, with the unrelated code folded away.
2. **Logic inventory** — one row per rule with reference `file:line`: fields and
   constraints (length in *bytes* where encoding matters, required, format, range,
   default), client validations, cross-field `onChange` mutations, conditional
   enable/show/hide, role/date-dependent defaults, server checks (optimistic locking,
   referential), side effects (downstream writes, audit logs, notifications, jobs,
   files), error messages and error-display paths, implicit per-instance state. [deep]
3. **Pattern extraction** — how already-ported areas in the new repos are structured
   (file set, store, validation schema, API model, tests). Pick 1–2 reference siblings.
   [standard, read-only subagents]
4. **Gap analysis** — inventory ⊖ existing new implementation. [deep]
4b. Read `docs/design-principles.md`; the new code follows it (separation of concerns
   across the layer split, DRY of rules not lines, no speculative options).
5. **Layer split** — decide where each rule lives. Integrity rules must exist on the
   **server** (a client-only check is a correctness hole); UX rules on the client;
   many need both. [deep]
6. **Generate** — mechanical scaffolding anchored on the sibling files [standard];
   logic-heavy code (validation, business rules, side effects) [deep]; tests per the
   repo's convention, one per inventory rule that is testable [deep marks, standard
   writes].
   **Comments:** carry the reference's comments over as they are onto the equivalent
   new code (that is what makes line-by-line comparison possible). New comments follow
   `docs/design-principles.md` § Comments and go only on code or behavior the
   reference does not have; ported code gets no new comments.
7. **Verify** — dispatch `completeness-verifier` (inventory vs implementation, item by
   item) and `fix-verifier` (client value ⇄ API schema ⇄ DB constraint). Run the
   generated tests to green. Any MISSING / WEAKENED / LAYER GAP / UNTESTED → not done.
8. **Deliver** — *what I need from you* first, then summary, inventory table with new-code locations, PR draft. [light]

## Common port gaps to design against
- Per-instance dialogs in the reference vs long-lived module stores in the new app →
  reset on mount/unmount.
- Empty string ≡ NULL semantics in some databases; `NOT NULL` fixed-width columns
  needing a placeholder value rather than `null` defaults.
- Silent error drops on action callbacks where the reference displayed the error.
- Byte-length vs character-length limits; full-width input; IME behavior.
- Option lists, default selections, and value→label mappings.
- Date/calendar/locale edge cases; resubmit; modal reopen; role variations.
