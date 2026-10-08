"""Parse a source file into symbols and render folded slices of it.

Uses tree-sitter (pip install tree-sitter-language-pack) when available; otherwise a
brace/regex fallback that handles C-family languages less precisely.
"""
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

try:
    from tree_sitter_language_pack import get_parser as _ts_parser
except Exception:  # package missing or broken: fallback mode
    _ts_parser = None
if os.environ.get("CODE_SLICE_FALLBACK"):
    _ts_parser = None

LANG_BY_EXT = {
    ".ts": "typescript", ".mts": "typescript", ".cts": "typescript", ".tsx": "tsx",
    ".js": "javascript", ".jsx": "javascript", ".mjs": "javascript", ".cjs": "javascript",
    ".java": "java", ".cs": "csharp", ".py": "python", ".kt": "kotlin", ".kts": "kotlin",
    ".go": "go", ".php": "php", ".vb": "vb", ".c": "c", ".h": "c", ".cpp": "cpp", ".cc": "cpp",
    ".hpp": "cpp", ".rs": "rust", ".rb": "ruby", ".scala": "scala", ".swift": "swift", ".vue": "vue",
}
SQL_EXTS = {".sql", ".pks", ".pkb", ".pls", ".plsql", ".prc", ".fnc", ".trg", ".vw", ".pck"}

CONTAINERS = {
    "class_declaration", "abstract_class_declaration", "interface_declaration", "enum_declaration",
    "namespace_declaration", "file_scoped_namespace_declaration", "struct_declaration",
    "record_declaration", "internal_module", "module", "class_definition", "class_specifier",
    "struct_specifier", "impl_item", "trait_item", "object_declaration", "class", "type_spec",
    "class_block", "module_block", "structure_block", "interface_block",
}
CALLABLES = {
    "function_declaration", "generator_function_declaration", "method_definition", "method_declaration",
    "constructor_declaration", "function_definition", "local_function_statement", "operator_declaration",
    "destructor_declaration", "function_item", "method", "singleton_method", "function_signature",
    "abstract_method_signature", "annotation_type_declaration",
}
LEAF_DECLS = {"type_alias_declaration", "property_declaration", "enum_member_declaration_list"}
FUNC_VALUES = {"arrow_function", "function_expression", "function", "generator_function", "lambda_expression"}
FOLD_EXTRA = {"object", "array", "jsx_element", "arguments", "switch_body", "switch_block", "object_type",
              "template_string", "initializer_expression", "array_initializer", "comment",
              "argument_list", "jsx_expression", "parenthesized_expression", "string"}
NAME_FIELDS = ("name", "declarator")


def read_text(path):
    raw = Path(path).read_bytes()
    for enc in ("utf-8-sig", "cp932", "cp1252"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1")


def split_lines(text):
    """Split on \n only, like editors and rg (str.splitlines also splits on NEL, FF, U+2028…)."""
    lines = [l[:-1] if l.endswith("\r") else l for l in text.split("\n")]
    if lines and lines[-1] == "":
        lines.pop()
    return lines


def lang_of(path):
    ext = Path(path).suffix.lower()
    if ext in SQL_EXTS:
        return "sql"
    return LANG_BY_EXT.get(ext)


@dataclass(eq=False)
class Symbol:
    name: str
    kind: str
    start: int            # 1-based, first line of the declaration (after leading comments)
    end: int
    depth: int
    parent: "Symbol" = None
    doc_start: int = 0    # first line including leading comments/annotations
    sig: str = ""
    callable: bool = False

    @property
    def qname(self):
        parts, s = [], self
        while s:
            if s is self or s.kind not in ("namespace", "file_scoped_namespace", "internal_module", "module"):
                parts.append(s.name)
            s = s.parent
        return ".".join(reversed(parts))


@dataclass
class Parsed:
    path: str
    lang: str
    lines: list
    symbols: list = field(default_factory=list)
    intervals: list = field(default_factory=list)   # foldable (start, end) line pairs
    calls: list = field(default_factory=list)       # (line, callee_name, receiver or None)
    tree: object = None


_CACHE = {}


def parse(path, text=None, rev=None):
    """Parse a file (or `text` standing in for it, e.g. a git revision)."""
    key = str(Path(path).resolve()) + (f"@{rev}" if rev else "")
    if key in _CACHE:
        return _CACHE[key]
    if text is None:
        text = read_text(path)
    lines = split_lines(text)
    lang = lang_of(path) or "text"
    p = Parsed(str(Path(path).resolve()), lang, lines)
    if lang == "sql":
        _sql_symbols(p)
    elif _ts_parser and lang != "text":
        try:
            _ts_parse(p, text, lang)
        except Exception:
            _fallback(p)
    else:
        _fallback(p)
    for s in p.symbols:
        s.doc_start = _leading_doc(lines, s.start, lang)
        s.sig = _signature(lines, s)
    _CACHE[key] = p
    return p


# ───────────── tree-sitter ─────────────

KIND_ALIAS = {"class_block": "class", "module_block": "module", "structure_block": "struct",
              "interface_block": "interface", "type_spec": "type", "class_specifier": "class",
              "struct_specifier": "struct", "impl_item": "impl", "trait_item": "trait"}
ID_TYPES = ("identifier", "simple_identifier", "type_identifier", "field_identifier", "constant", "name")


def _node_name(n, src):
    for f in NAME_FIELDS:
        c = n.child_by_field_name(f)
        if c is not None:
            if c.type in ("function_declarator", "pointer_declarator"):
                c = c.child_by_field_name("declarator") or c
            return src[c.start_byte:c.end_byte].decode("utf-8", "replace")
    c = next((c for c in n.named_children if c.type in ID_TYPES), None)
    return src[c.start_byte:c.end_byte].decode("utf-8", "replace") if c is not None else None


def _callee(n, src):
    """(name, receiver) of a call node: `api.save(x)` -> ("save", "api")."""
    f = n.child_by_field_name("function") or n.child_by_field_name("name") or n.child_by_field_name("method")
    recv = n.child_by_field_name("object")
    if f is None and n.named_children:
        f = n.named_children[0]
    if f is None:
        return None, None
    if f.type in ("member_expression", "member_access_expression", "field_access", "attribute",
                  "scoped_identifier", "qualified_name", "navigation_expression"):
        recv = f.child_by_field_name("object") or f.child_by_field_name("expression") or (
            f.named_children[0] if f.named_children else None)
        prop = (f.child_by_field_name("property") or f.child_by_field_name("name")
                or f.child_by_field_name("field") or f.child_by_field_name("attribute"))
        if prop is None and f.named_children:
            prop = f.named_children[-1]
        f = prop
    if f is None:
        return None, None
    t = src[f.start_byte:f.end_byte].decode("utf-8", "replace")
    m = re.search(r"[A-Za-z_$][\w$]*$", t)
    r = src[recv.start_byte:recv.end_byte].decode("utf-8", "replace") if recv is not None else None
    return (m.group(0) if m else None), (r if r and re.fullmatch(r"[A-Za-z_$][\w$]*", r) else None)


def _callee_name(n, src):
    return _callee(n, src)[0]


CALL_TYPES = {"call_expression", "method_invocation", "invocation_expression", "call",
              "new_expression", "object_creation_expression"}


def _ts_parse(p, text, lang):
    src = text.encode("utf-8")
    tree = _ts_parser(lang).parse(src)
    p.tree = tree
    stack = []

    def visit(n, parent_sym, depth):
        sym = None
        t = n.type
        if n.is_named:
            s_row = n.start_point[0] + 1
            e_row = max(s_row, n.end_point[0] + (1 if n.end_point[1] > 0 else 0))
            name, kind, is_call = None, None, False
            if t in CONTAINERS:
                name, kind = _node_name(n, src), KIND_ALIAS.get(t) or t.replace("_declaration", "").replace("_definition", "")
            elif t in CALLABLES:
                name, kind, is_call = _node_name(n, src), t.replace("_declaration", "").replace("_definition", ""), True
            elif t in LEAF_DECLS and e_row > s_row:
                name, kind = _node_name(n, src), t.replace("_declaration", "")
                is_call = t == "property_declaration"
            elif t in ("variable_declarator", "public_field_definition", "field_definition", "pair",
                       "property_signature", "assignment_expression"):
                val = n.child_by_field_name("value") or n.child_by_field_name("right")
                if val is not None and (val.type in FUNC_VALUES or _wraps_function(val)):
                    name = _node_name(n, src) or (n.child_by_field_name("key") and
                                                  src[n.child_by_field_name("key").start_byte:
                                                      n.child_by_field_name("key").end_byte].decode())
                    if name is None and n.child_by_field_name("left") is not None:
                        lf = n.child_by_field_name("left")
                        name = src[lf.start_byte:lf.end_byte].decode().split(".")[-1]
                    kind, is_call = "function", True
            elif t in FUNC_VALUES and e_row - s_row >= 2 and n.parent is not None and n.parent.type in ("arguments", "argument_list"):
                call = n.parent.parent
                cn = _callee_name(call, src) if call is not None else None
                name, kind, is_call = f"{cn or 'callback'}(=>)", "callback", True
            if name:
                sym = Symbol(name.strip(), kind, s_row, e_row, depth, parent_sym, callable=is_call)
                p.symbols.append(sym)
            if e_row - s_row >= 2 and (t in FOLD_EXTRA or t.endswith("block") or t.endswith("body")
                                       or t.endswith("_list") and t != "formal_parameters"):
                p.intervals.append((s_row, e_row))
            if t in CALL_TYPES:
                cn, recv = _callee(n, src)
                if cn:
                    p.calls.append((s_row, cn, recv))
        nxt_parent = sym or parent_sym
        for c in n.children:
            visit(c, nxt_parent, depth + (1 if sym else 0))

    import sys
    sys.setrecursionlimit(max(10000, sys.getrecursionlimit()))
    visit(tree.root_node, None, 0)


def _wraps_function(val):
    """`React.memo(() => …)`, `useCallback(async () => …)`, `forwardRef(function X() …)`."""
    if val.type not in ("call_expression",):
        return False
    args = val.child_by_field_name("arguments")
    return bool(args and any(a.type in FUNC_VALUES or _wraps_function(a) for a in args.named_children))


# ───────────── fallback (no tree-sitter) ─────────────

SIG_RE = [
    (re.compile(r"^\s*(?:export\s+)?(?:default\s+)?(?:abstract\s+)?(?:public\s+|private\s+|protected\s+|internal\s+|static\s+|sealed\s+|partial\s+|final\s+)*"
                r"(class|interface|enum|struct|namespace|record)\s+([A-Za-z_][\w.]*)"), "container"),
    (re.compile(r"^\s*(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s*\*?\s*([A-Za-z_$][\w$]*)"), "function"),
    (re.compile(r"^\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*(?::[^=]+)?=\s*(?:async\s+)?(?:\([^)]*\)|[A-Za-z_$][\w$]*)\s*(?::[^=]+)?=>"), "function"),
    (re.compile(r"^\s*(?:(?:public|private|protected|internal|static|final|override|virtual|abstract|async|synchronized|sealed|extern|new|unsafe)\s+)+"
                r"[\w<>\[\],.?\s]*?\b([A-Za-z_]\w*)\s*\([^;]*$"), "method"),
    (re.compile(r"^\s*(?:Public|Private|Protected|Friend|Shared|Overrides|Overridable|\s)*(Sub|Function|Property)\s+([A-Za-z_]\w*)", re.I), "vb"),
]
KEYWORDS = {"if", "for", "while", "switch", "catch", "return", "new", "else", "do", "try", "using", "lock", "foreach"}


def _brace_pairs(lines):
    pairs, stack = [], []
    in_block = False
    for i, line in enumerate(lines, 1):
        j, n, q = 0, len(line), None
        while j < n:
            ch = line[j]
            if in_block:
                if line.startswith("*/", j):
                    in_block, j = False, j + 2
                    continue
                j += 1
                continue
            if q:
                if ch == "\\":
                    j += 2
                    continue
                if ch == q:
                    q = None
                j += 1
                continue
            if line.startswith("//", j):
                break
            if line.startswith("/*", j):
                in_block, j = True, j + 2
                continue
            if ch in "\"'`":
                q = ch
            elif ch == "{":
                stack.append(i)
            elif ch == "}" and stack:
                pairs.append((stack.pop(), i))
            j += 1
        if q in ("'", '"'):
            q = None
    return pairs


def _fallback(p):
    pairs = _brace_pairs(p.lines)
    opens = {}
    for s, e in pairs:
        opens[s] = max(e, opens.get(s, 0))
        if e - s >= 2:
            p.intervals.append((s, e))
    syms = []
    for i, line in enumerate(p.lines, 1):
        for rx, kind in SIG_RE:
            m = rx.match(line)
            if not m:
                continue
            name = m.group(m.lastindex)
            if name in KEYWORDS:
                break
            end = None
            for k in range(i, min(i + 6, len(p.lines)) + 1):
                if k in opens:
                    end = opens[k]
                    break
            if kind == "vb":
                endrx = re.compile(r"^\s*End\s+" + m.group(1), re.I)
                end = next((k for k in range(i + 1, len(p.lines) + 1) if endrx.match(p.lines[k - 1])), None)
            if end:
                syms.append(Symbol(name, "class" if kind == "container" else kind, i, end, 0,
                                   callable=kind != "container"))
            break
    syms.sort(key=lambda s: (s.start, -s.end))
    stack = []
    for s in syms:
        while stack and not (stack[-1].start <= s.start and s.end <= stack[-1].end):
            stack.pop()
        if stack:
            s.parent, s.depth = stack[-1], stack[-1].depth + 1
        stack.append(s)
    p.symbols = syms
    for i, line in enumerate(p.lines, 1):
        for m in re.finditer(r"\b([A-Za-z_$][\w$]*)\s*\(", line):
            if m.group(1) not in KEYWORDS:
                p.calls.append((i, m.group(1), None))


# ───────────── SQL / PL-SQL ─────────────

SQL_OBJ_RE = re.compile(
    r"^\s*CREATE\s+(?:OR\s+REPLACE\s+)?(?:EDITIONABLE\s+|NONEDITIONABLE\s+)?(?:FORCE\s+)?(?:GLOBAL\s+TEMPORARY\s+)?"
    r"(PACKAGE\s+BODY|PACKAGE|PROCEDURE|FUNCTION|TRIGGER|VIEW|MATERIALIZED\s+VIEW|TABLE|TYPE\s+BODY|TYPE|SEQUENCE|INDEX|UNIQUE\s+INDEX|SYNONYM)\s+"
    r"(?:IF\s+NOT\s+EXISTS\s+)?([\"\w.$#]+)", re.I)
SQL_MEMBER_RE = re.compile(r"^\s*(PROCEDURE|FUNCTION)\s+([\"\w$#]+)", re.I)
SQL_END_RE = re.compile(r"^\s*/\s*$")


def _sql_symbols(p):
    lines = p.lines
    objs = []
    for i, line in enumerate(lines, 1):
        m = SQL_OBJ_RE.match(line)
        if m:
            objs.append([m.group(2).strip('"').split(".")[-1], re.sub(r"\s+", " ", m.group(1)).lower(), i])
    for k, (name, kind, start) in enumerate(objs):
        nxt = objs[k + 1][2] - 1 if k + 1 < len(objs) else len(lines)
        end = nxt
        for j in range(start, nxt + 1):
            t = lines[j - 1]
            if SQL_END_RE.match(t):
                end = j
                break
            if kind in ("table", "view", "sequence", "index", "unique index", "synonym", "materialized view") and t.rstrip().endswith(";"):
                end = j
                break
        while end > start and not lines[end - 1].strip():
            end -= 1
        obj = Symbol(name, kind, start, end, 0, callable=kind in ("procedure", "function", "trigger"))
        p.symbols.append(obj)
        if kind in ("package body", "package", "type body"):
            members = [(j, SQL_MEMBER_RE.match(lines[j - 1])) for j in range(start + 1, end + 1)]
            members = [(j, m) for j, m in members if m]
            for idx, (j, m) in enumerate(members):
                name_m = m.group(2).strip('"')
                stop = members[idx + 1][0] - 1 if idx + 1 < len(members) else end
                decl_end = _sql_forward_decl(lines, j, stop)
                if decl_end or kind == "package":
                    p.symbols.append(Symbol(name_m, m.group(1).lower() + " decl", j, decl_end or j, 1, obj))
                    continue
                endrx = re.compile(r"^\s*END\s+" + re.escape(name_m) + r"\s*;", re.I)
                mend = next((q for q in range(j, stop + 1) if endrx.match(lines[q - 1])), None)
                if mend is None:
                    mend = stop
                    if kind == "package":
                        mend = next((q for q in range(j, stop + 1) if lines[q - 1].rstrip().endswith(";")), stop)
                p.symbols.append(Symbol(name_m, m.group(1).lower(), j, mend, 1, obj, callable=True))
    for s in p.symbols:
        p.intervals.extend(_sql_blocks(lines, s.start, s.end))


def _sql_forward_decl(lines, j, stop):
    """End line if the member at j is only a declaration (`…;` before any IS/AS), else None."""
    for q in range(j, min(stop, j + 40) + 1):
        t = re.sub(r"--.*$", "", lines[q - 1])
        if re.search(r"\b(IS|AS)\b", t, re.I):
            return None
        if t.rstrip().endswith(";"):
            return q
    return None


def _sql_blocks(lines, a, b):
    stack, out = [], []
    for j in range(a, b + 1):
        t = lines[j - 1].strip().upper()
        if re.match(r"^(BEGIN|LOOP|IF\b.*\bTHEN$|CASE\b|FOR\b.*\bLOOP$|WHILE\b.*\bLOOP$|DECLARE)", t):
            stack.append(j)
        elif re.match(r"^END(\s+(IF|LOOP|CASE))?\b", t) and stack:
            s = stack.pop()
            if j - s >= 2:
                out.append((s, j))
    return out


# ───────────── queries ─────────────

def _leading_doc(lines, start, lang, cap=25):
    pat = r"^\s*(//|/\*|\*|--|#(?!region|endregion|if|else|endif|pragma)|''')"
    if lang in ("java", "typescript", "tsx", "javascript", "python", "kotlin"):
        pat += r"|^\s*@\w"
    if lang in ("csharp", "vb"):
        pat += r"|^\s*\[[A-Z]\w*|^\s*<\w+"
    rx = re.compile(pat)
    k = start - 1
    while k >= 1 and start - k <= cap and rx.match(lines[k - 1]):
        k -= 1
    return k + 1


def _signature(lines, s, width=160):
    text = lines[s.start - 1].strip() if s.start <= len(lines) else ""
    if not text.endswith(("{", "=>", ")")) and s.end > s.start:
        nxt = lines[s.start].strip() if s.start < len(lines) else ""
        if nxt and len(text) + len(nxt) < width:
            text += " " + nxt
    return text[:width]


def symbols_at(p, line):
    """Innermost-first list of symbols containing `line`."""
    hits = [s for s in p.symbols if s.doc_start <= line <= s.end]
    return sorted(hits, key=lambda s: (s.end - s.start, -s.start))


def enclosing(p, line, prefer="callable", level=0):
    hits = symbols_at(p, line)
    if prefer == "callable":
        named = [s for s in hits if s.callable and s.kind != "callback"]
        pick = named or [s for s in hits if s.callable] or hits
    elif prefer == "outer":
        pick = list(reversed([s for s in hits if s.callable] or hits))
    else:
        pick = hits
    if not pick:
        return None
    return pick[min(level, len(pick) - 1)]


def label_at(p, line):
    """`Outer.method > useEffect(=>) > then(=>)` — named function plus the callbacks the line sits in."""
    hits = symbols_at(p, line)
    named = next((s for s in hits if s.callable and s.kind != "callback"), None) or (hits[0] if hits else None)
    if not named:
        return "(top level)"
    cbs = [s for s in hits if s.kind == "callback" and s.start >= named.start and s is not named]
    return " > ".join([named.qname] + [c.name for c in reversed(cbs[:3])])


def by_name(p, name):
    parts = name.split(".")
    out = []
    for s in p.symbols:
        if s.name == parts[-1] or s.name.strip('"').upper() == parts[-1].upper() and p.lang == "sql":
            q = s.qname.split(".")
            if len(parts) == 1 or q[-len(parts):] == parts:
                out.append(s)
    return out


# ───────────── rendering ─────────────

def render(p, start, end, targets=(), mode="auto", max_lines=150, around=6, sym=None, fold_min=4,
           protect=()):
    """Return text of lines [start, end] with non-target blocks folded to fit max_lines.

    mode: full (no folding) · auto (fold only if over budget) · around (targets ± around).
    `protect` intervals are never folded (e.g. the symbol's own body).
    """
    lines = p.lines
    end = min(end, len(lines))
    targets = sorted({t for t in targets if start <= t <= end})
    total = end - start + 1
    if mode == "full" or (mode == "auto" and total <= max_lines):
        return _emit(lines, [("L", i) for i in range(start, end + 1)], targets, start, end, total)

    inner = [(a, b) for a, b in p.intervals if start <= a and b <= end and (a, b) not in protect
             and not (sym and b >= sym.end and a <= sym.start + 2)]
    inner = sorted(set(inner), key=lambda ab: (ab[0], -ab[1]))

    def plan(threshold):
        folded = []
        for a, b in inner:
            if b - a - 1 < max(threshold, fold_min):
                continue
            if any(fa < a and b < fb for fa, fb in folded) or any(a < fa and fb < b for fa, fb in folded):
                continue
            if any(a <= t <= b for t in targets):
                continue
            folded.append((a, b))
        items, i = [], start
        fold_at = {a: b for a, b in folded}
        while i <= end:
            if i in fold_at:
                b = fold_at[i]
                items.append(("L", i))
                if b - i - 1 > 0:
                    items.append(("F", i + 1, b - 1))
                items.append(("L", b))
                i = b + 1
            else:
                items.append(("L", i))
                i += 1
        return items

    if mode == "around":
        items = [("L", i) for i in range(start, end + 1)]
    else:
        items = None
        for th in (40, 20, 10, 6, fold_min):
            items = plan(th)
            if _count(items) <= max_lines:
                break
    if _count(items) > max_lines or mode == "around":
        items = _window(p, items, targets, start, end, sym, around if mode == "around" else None, max_lines)
    return _emit(lines, items, targets, start, end, total)


def _count(items):
    return sum(1 for it in items if it[0] == "L") + sum(1 for it in items if it[0] == "F")


def _window(p, items, targets, start, end, sym, ctx, max_lines):
    """Keep header lines, ancestor block lines of targets and ±ctx around targets; elide the rest."""
    head_end = start
    if sym:
        k = sym.start
        while k < min(sym.end, sym.start + 4) and not re.search(r"[{:]\s*$|=>\s*\{?\s*$|\bIS\b|\bAS\b\s*$", p.lines[k - 1]):
            k += 1
        head_end = k
    anchors = set(range(start, head_end + 1)) | {end}
    for t in targets:
        for a, b in p.intervals:
            if a <= t <= b and start <= a and b <= end:
                anchors.update((a, b))
                k = a - 1
                if p.lines[a - 1].strip().startswith("{"):
                    while k >= start and not p.lines[k - 1].strip():
                        k -= 1
                    if k >= start:
                        anchors.add(k)
    widths = [ctx] if ctx is not None else [8, 5, 3, 2, 1, 0]
    best = None
    for w in widths:
        keep = set(anchors)
        for t in targets:
            keep.update(range(t - w, t + w + 1))
        if not targets:
            budget = max_lines - len(anchors)
            keep.update(range(start, start + max(budget, 10)))
        out, run = [], []

        def flush():
            if sum(1 for r in run if r[0] == "L") == len(run) and len(run) <= 2:
                out.extend(run)
            elif run:
                out.append(("F", run[0][1], run[-1][2] if run[-1][0] == "F" else run[-1][1]))
            run.clear()

        for it in items:
            if it[0] == "L" and it[1] in keep:
                flush()
                out.append(it)
            else:
                run.append(it)
        flush()
        best = out
        if _count(out) <= max_lines:
            break
    return best


def clip(text, width=220):
    return text if len(text) <= width else text[:width] + f" …[+{len(text) - width} chars]"


def _emit(lines, items, targets, start, end, total):
    tset = set(targets)
    w = len(str(end))
    out = []
    for it in items:
        if it[0] == "L":
            n = it[1]
            mark = ">" if n in tset else " "
            out.append(f"{mark}{n:>{w}}| {clip(lines[n - 1].rstrip())}")
        else:
            a, b = it[1], it[2]
            n = b - a + 1
            out.append(f" {'':>{w}}| ... {n} line{'s' if n > 1 else ''} folded (L{a}-{b})")
    shown = sum(1 for it in items if it[0] == "L")
    return "\n".join(out), shown, total
