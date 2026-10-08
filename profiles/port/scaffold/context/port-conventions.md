# Port conventions — reference → target

How reference concepts map to the new stack. Fill before the first area is ported;
every port follows it.

## Concept mapping
| reference concept | target equivalent | notes |
| --- | --- | --- |
| screen / form class | page + form component + store |  |
| server action / handler | route → controller → service → persister |  |
| stored procedure / SQL file | persister query |  |
| error message table | message catalog + error codes |  |

## Naming
<!-- how reference IDs/names translate to file and symbol names -->

## Data rules
- Empty string vs NULL semantics of the database.
- Length limits in **bytes** vs characters for the DB encoding.
- Fixed-width / NOT NULL columns and their placeholder values.
- Date / calendar / locale handling.

## State and lifecycle
- Reference dialogs/forms that were per-instance → reset target stores on mount/unmount.

## Error display
- Every reference error path that showed a message must show one in the target.

## Comments
- Reference comments are carried over as they are onto the equivalent target code.

## Out of scope / deliberately changed
| area | change | requested by (spec-changes.json entry) |
| --- | --- | --- |
