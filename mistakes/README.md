# mistakes/ — the agent's mistake log

One markdown file per **class** of mistake the agent has made in this workspace, so
the same mistake is not repeated. Agents read `INDEX.md` before non-trivial work and
open the files whose triggers match; they add or update a file whenever a mistake is
caught. Rules: AGENTS.md §10.

- `INDEX.md` — one line per file: name, severity, the symptoms/triggers that mean
  "read me". Keep it short; it is read at the start of every task.
- `_TEMPLATE.md` — copy it for a new class.
- `<issue-class>.md` — named after the class, never after an item
  (`static-read-of-runtime-bug.md`, not `bug-412.md`).

What belongs here vs elsewhere:

| Here (`mistakes/`) | Elsewhere |
| --- | --- |
| Something the **agent did wrong** and how to not do it again | Environment facts / tool recipes → `docs/verification-guide.md`, `context/` |
| The rule, the check, and a log of occurrences | Cross-cutting rules that proved themselves → promoted into `AGENTS.md` / a workflow step |
| Blameless, generalized, no customer data or secrets | Item-specific narratives → `reports/` |

The seeded files come from a previous engagement; their occurrence logs start empty
for this project.
