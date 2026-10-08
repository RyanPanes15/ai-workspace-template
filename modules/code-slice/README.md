# code-slice — read the lines a task needs, not the files

`cs.py` parses source files (tree-sitter when installed, a brace heuristic otherwise),
finds the function, block or object that matters, and prints it with line numbers,
**folding** the blocks that don't contain the target. Everything is read-only.

```
pip install tree-sitter-language-pack      # optional, recommended (exact boundaries)
python modules/code-slice/cs.py --help
python modules/code-slice/tests/test_code_slice.py [--fallback]
```

Repos come from `workspace.config.json`; paths print as `<workspace path>` or
`<repo>/<path>`. Files can be named by full path, `repo:path`, a unique path suffix
or just a unique file name.

## Commands by task

| Task | Command | Prints |
| --- | --- | --- |
| Shape of a file / folder | `outline PATH... [--depth N] [--sig] [--callbacks]` | symbols with line ranges (one line each) |
| The code around a line | `show file:LINE [--around N] [--outer] [--level K]` | the enclosing function, target marked `>` |
| A named function/class | `show Name` · `show Class.method` · `show file#Name` | that symbol (first definition; others listed) |
| An exact range | `show file:120-160` | those lines |
| Where something is defined | `find Name [--show]` | `file:start-end kind name — signature` |
| Who uses it | `refs Name [--in PATH]` | hits grouped by enclosing function (`Fn > useEffect(=>)`) |
| Bug: stack trace / log | `trace log.txt` (or `-` for stdin) | innermost repo frame in full (folded), callers ±N lines |
| Bug: the process flow | `flow file#Fn [--depth 1] [--up 1] [--in PATH]` | the function, the repo functions it calls, its callers |
| Port / feature: how a field is done elsewhere | `field name [--scope DIR] [--alias X] [--show]` | every place it appears, by layer and function; `--show` adds folded slices |
| Review | `diff REPO [BASE \| A..B \| A...B] [--staged]` | changed functions only, changed lines marked |
| DB | `sql NAME` · `sql --column COL` | one table/view/procedure/package member · tables + code carrying a column |
| Big JSON/YAML | `json FILE --keys` · `--path a.b` · `--find X` | structure, one subtree, matching paths |

Budgets: `--max-lines` per slice (default 150; 120 for flow/trace, 80 for field/diff)
and `--budget` for the whole command (default 400–600). Over budget, nested blocks
without a target are folded (largest first), then lines far from the targets are
elided; anything left out is listed as `... N lines folded (La-b)` and can be fetched
with `show file:a-b`.

## What it understands

- **Languages (tree-sitter):** TypeScript/TSX, JavaScript, Java, C#, Python, Kotlin, Go,
  PHP, C/C++, Rust, Ruby, Scala, Swift, VB. React arrow components, `useCallback`/
  `memo`/`forwardRef` wrappers, class fields holding arrows, object-literal methods and
  callbacks passed to calls (`useEffect(=>)`) are symbols.
- **SQL / PL-SQL (regex):** `CREATE [OR REPLACE] TABLE|VIEW|PROCEDURE|FUNCTION|PACKAGE
  [BODY]|TRIGGER|TYPE…`, package members (`END name;`), forward declarations.
- **Stack traces:** Node/V8 (`at fn (file:line:col)`, `webpack:///`), Java
  (`at pkg.Class.m(File.java:N)` → package path), .NET in English and Japanese
  (`in … :line N` / `場所 … :行 N`), Python, and any `path:line`.
- **Imports (flow):** relative imports, tsconfig/jsconfig `baseUrl` + `paths` aliases
  (with `extends`), member calls on an imported object (`Api.save()` → `Api`'s file).
- **Encodings:** UTF-8, Shift-JIS (cp932) and cp1252 source files; output is UTF-8.
- **Field variants:** `orderDate` also matches `OrderDate`, `order_date`, `ORDER_DATE`,
  `order-date`, as substrings by default (so WinForms `txtOrderDate` and
  `dtpOrderDate` match); `--word` for whole words, `--alias` for labels or legacy names.

## Limits (say so in reports when they matter)

- Calls through dependency injection, interfaces, events, string-keyed dispatch or
  store objects are not followed; `flow` lists them as "not in the repos" or
  "several definitions" — follow those with `find` / `refs`.
- Without tree-sitter, one-line arrow functions are not symbols and Python is not
  folded.
- SQL inside Java strings or XML mappers is found by `refs`/`field`, not parsed.
- A trace line beyond the end of the file means the log came from a different build;
  check the deployed version before reading the code.
- Minified bundle frames resolve only after `modules/log-triage` symbolication.

See `docs/code-slice-scope.md` for the scope, design and test results.
