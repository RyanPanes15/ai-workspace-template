# Code slices — scope, design and test results

**Goal:** the agent reads the lines a task needs (a function, the block a bug sits in,
the call chain, the places a field is handled) instead of whole files. Large legacy
and screen files often run 2,000–9,000 lines; one whole-file read can take more context
than the rest of the task.

Tool: `modules/code-slice/cs.py` (usage in its README). Rule: AGENTS.md §4 item 8.
Mistake class: `mistakes/whole-file-read.md`.

## 1. Scope — tasks and the command that serves each

| Project type | Task | Input the agent has | Command | What comes back |
| --- | --- | --- | --- | --- |
| Maintenance | Bug with a stack trace | log / trace text | `trace log.txt` | the innermost repo function (folded around the failing line) and each caller ±6 lines; frames outside the repos listed |
| Maintenance | Bug at a known line | `file:line` from the report or a log | `show file:LINE` | the enclosing function; sibling blocks folded |
| Maintenance | Bug in a process flow | entry function | `flow file#Fn --up 1` | the function, the repo functions it calls, the functions that call it |
| Maintenance | Regression candidates | changed function | `refs Fn` | callers grouped by function, one line each |
| Port / feature | Field or feature already on another screen | field name, reference screen folder | `field name --scope DIR --show` | every read/validate/save/display site, by layer and function, with folded slices |
| Port | Inventory of a reference screen | folder | `outline DIR` then `field` per field | symbol map, then the code of each rule |
| Feature | Reuse a component | component name | `find Name`, `refs Name` | definition and consumers to regression-test |
| Any | Review | repo + base | `diff REPO A...B` | changed functions only, changed lines marked |
| Any | DB question | table / procedure / column | `sql NAME`, `sql --column COL` | one object; tables and code carrying the column |
| Any | Big JSON/YAML (OpenAPI, i18n, fixtures) | file + key | `json FILE --find X`, `--path a.b` | matching paths and one subtree |

Out of scope: semantic search (embeddings), runtime tracing, cross-service call
graphs through HTTP. The existing modules keep their jobs: `area-index` (area → files),
`log-triage` (log clustering, symbolication), `payload-decode`.

## 2. Design

1. **Locate** — files by path, `repo:path`, unique suffix or name (fast direct-path
   probe first, then the repo file list); text hits with ripgrep (Python fallback).
2. **Parse** — tree-sitter gives symbols (functions, methods, classes, arrow
   components, callbacks passed to calls), foldable blocks and call sites; SQL uses a
   regex parser for objects and package members; a brace heuristic covers missing
   grammars. Shift-JIS/cp1252 are decoded; line numbers match editors (split on `\n` only).
3. **Choose the region** — the enclosing function (innermost by default, `--outer` /
   `--level` to widen), leading doc comments and annotations included.
4. **Fold to budget** — if the region exceeds `--max-lines`, blocks without a target
   are folded largest-first; then lines far from the targets are elided, keeping the
   signature and the header line of every block that contains a target (including
   Allman-style `if (…)` / `{`). Every omission is printed as `... N lines folded (La-b)`.
5. **Budget the whole command** — `--budget` caps total output; slices that don't fit
   are listed as one-line pointers.

## 3. Test results

Fixture suite: `python modules/code-slice/tests/test_code_slice.py` — 20 cases with
tree-sitter, 19 in fallback mode (TS/TSX, C# in Shift-JIS, Java, PL/SQL, Python, Go,
Kotlin, VB, PHP; Node, Java and Japanese .NET traces; tsconfig path aliases; diff of
working tree and of a commit range). All pass in both modes.

Real-world run against a production multi-repo port workspace (web client, legacy
desktop reference client, legacy reference server, database packages), read-only:

| Scenario | Source size | Output |
| --- | --- | --- |
| `show` a line in a screen component | ~3k-line file; ~300-line handler | ~130 lines (the handler, folded) |
| `trace` a server null-reference exception | ~9k-line class; ~1k-line method | ~40 lines + ~15 for the caller |
| `flow` a UI event handler | handler + 2 callees in files of ~500 and 1k+ lines (resolved through path aliases) | ~80 lines |
| `field` across a reference screen and the new screen (~2k and ~3k lines, one in a legacy encoding) | ~30 hits in ~10 functions | ~20-line map; ~350 lines with `--show` |
| `sql` package member | ~800-line package body, member also forward-declared | the ~140-line function (declaration skipped) |
| `sql --column` | DDL folder, ~30 hits | table name + column line per hit |
| `diff` three merged commits | 5 files incl. a ~4k-line component | changed functions only, within the 600-line budget |

Reduction against reading the files involved: 83% (SQL member) to 99% (trace), above 95% in most cases.

Issues found and fixed during the run: encoding of grep hits in Shift-JIS files,
line drift from `str.splitlines` on NEL bytes, a skipped `packages/` folder that held
PL/SQL, namespace prefixes in names, PL/SQL forward declarations, trace resolution
listing every file (85 s → 0.4 s with the direct-path probe), path-alias imports.

## 4. Limits and next candidates

Limits are listed in `modules/code-slice/README.md` (dependency injection and event
dispatch not followed, no folding without tree-sitter for Python, SQL embedded in
strings found but not parsed).

Candidates, in order of expected value:
1. `diff --stdin` for `gh pr diff` output (review without a local checkout).
2. `screen <area>` — area-index files + outline of each, one command for a screen.
3. Parse cache in `_work/` for very large repos on slow disks.
4. Receiver-type resolution for Java/C# (`this.service.save` → the field's type).
