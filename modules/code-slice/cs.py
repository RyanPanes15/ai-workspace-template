#!/usr/bin/env python3
"""Print only the lines of code a task needs — not whole files.

  cs.py outline PATH...                      symbols + line ranges of files (or a folder's files)
  cs.py show TARGET [--full|--around N]      a function/class, folded to fit --max-lines
        TARGET: file:LINE · file:L1-L2 · file:L1,L2 · file#Symbol · Symbol · Class.method
  cs.py find NAME [--show]                   where NAME is defined (all repos)
  cs.py refs NAME [--in PATH] [--regex]      usages grouped by enclosing function (no bodies)
  cs.py flow TARGET [--depth 1] [--up 1]     a function + the functions it calls (+ its callers)
  cs.py trace [LOGFILE|-]                    stack trace / log -> the repo functions on it
  cs.py field NAME... [--scope PATH] [--show] every place a field/feature appears, by layer
  cs.py diff REPO [BASE] [--staged]          changed functions only, for review
  cs.py sql NAME | --column COL              a DB object (table, view, package member) or a column
  cs.py json FILE [--path a.b] [--find X]    one part of a large JSON/YAML file

Common flags: --max-lines N (per slice, default 150) · --budget N (total, default 400) ·
--repo NAME (limit search to repos) · --json (machine output for outline/find/refs/field).
Paths print relative to the workspace root. Lines marked '>' are the target lines;
'... N lines folded (La-b)' marks code left out — ask for it with `show file:a-b`.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from collections import OrderedDict, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import slicer as S  # noqa: E402

ROOT = Path(os.environ.get("CODE_SLICE_ROOT") or Path(__file__).resolve().parents[2])
for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

CODE_EXTS = set(S.LANG_BY_EXT) | S.SQL_EXTS
SKIP_DIRS = {"node_modules", ".git", "dist", "build", "out", "bin", "obj", "coverage", ".next", ".nuxt",
             "__pycache__", ".venv", "venv", "target", ".gradle", ".idea", ".vs", "vendor"}
SOURCE_ROOTS = ("", "src", "src/main/java", "src/main/kotlin", "app/src/main/java", "src/main/scala")
SKIP_FILE_RE = re.compile(r"(\.min\.js|\.map|\.lock|-lock\.json|\.snap|\.d\.ts)$")
STOP_CALLS = {
    "log", "warn", "error", "info", "debug", "push", "pop", "map", "filter", "forEach", "reduce", "find",
    "some", "every", "includes", "indexOf", "join", "split", "slice", "splice", "concat", "keys", "values",
    "entries", "assign", "then", "catch", "finally", "resolve", "reject", "toString", "valueOf", "trim",
    "replace", "substring", "substr", "toUpperCase", "toLowerCase", "parseInt", "parseFloat", "String",
    "Number", "Boolean", "Array", "Object", "Date", "Promise", "JSON", "parse", "stringify", "set", "get",
    "has", "add", "delete", "clear", "length", "useState", "useEffect", "useMemo", "useCallback", "useRef",
    "useContext", "setTimeout", "clearTimeout", "require", "super", "equals", "hashCode", "println", "print",
    "format", "append", "Add", "Remove", "Contains", "ToString", "Equals", "Format", "WriteLine", "Trim",
    "Substring", "Replace", "Split", "IsNullOrEmpty", "Parse", "TryParse", "size", "isEmpty", "contains",
    "put", "remove", "Error", "Exception", "len", "range", "str", "int", "isinstance", "getattr", "dict", "list",
}


# ───────────── workspace / files ─────────────

def config():
    p = ROOT / "workspace.config.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def repos(only=None):
    out = []
    for r in config().get("repos", []):
        p = Path(r["path"])
        p = p if p.is_absolute() else ROOT / p
        if p.exists() and (not only or r["name"] in only):
            out.append({"name": r["name"], "role": r.get("role", "other"), "path": p})
    if not out and not only:
        out.append({"name": ".", "role": "other", "path": ROOT})
    return out


def rel(path):
    """Workspace-relative path, or `<repo>/<path>` for repos outside the workspace."""
    rp = Path(path).resolve()
    try:
        return rp.relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        r = repo_of(rp)
        return f"{r['name']}/{rp.relative_to(r['path'].resolve()).as_posix()}" if r else rp.as_posix()


def repo_of(path):
    rp = Path(path).resolve()
    best = None
    for r in repos():
        try:
            rp.relative_to(r["path"].resolve())
            if best is None or len(str(r["path"])) > len(str(best["path"])):
                best = r
        except ValueError:
            continue
    return best


def _skip(path_parts):
    return any(p in SKIP_DIRS for p in path_parts)


_FILES = {}


def files(repo):
    key = str(repo["path"])
    if key in _FILES:
        return _FILES[key]
    out = []
    rg = shutil.which("rg")
    if rg:
        args = [rg, "--files", "--no-messages"] + [f"-g=!{d}/" for d in SKIP_DIRS]
        res = subprocess.run(args, cwd=repo["path"], capture_output=True, text=True, encoding="utf-8", errors="replace")
        out = [repo["path"] / l for l in res.stdout.splitlines() if l]
    else:
        for dp, dn, fn in os.walk(repo["path"]):
            dn[:] = [d for d in dn if d not in SKIP_DIRS and not d.startswith(".")]
            out.extend(Path(dp, f) for f in fn)
    out = [f for f in out if f.suffix.lower() in CODE_EXTS and not SKIP_FILE_RE.search(f.name)]
    _FILES[key] = out
    return out


def all_files(only=None):
    return [f for r in repos(only) for f in files(r)]


def resolve_file(spec, only=None):
    p = Path(spec)
    for cand in (p, ROOT / p):
        if cand.is_file():
            return cand.resolve()
    m = re.match(r"^([^:/\\]+)[:/\\](.+)$", spec)
    if m and not re.match(r"^[A-Za-z]:[\\/]", spec):
        for r in repos():
            if r["name"] == m.group(1) and (r["path"] / m.group(2)).is_file():
                return r["path"] / m.group(2)
    parts = [x for x in re.split(r"[\\/]+", spec) if x and x not in (".", "..")]
    if not parts:
        return None
    for k in range(len(parts) - 1):
        tail = Path(*parts[k:])
        for r in repos(only):
            for pre in SOURCE_ROOTS:
                cand = r["path"] / pre / tail
                if cand.is_file():
                    return cand.resolve()
    cands = [f for f in all_files(only) if f.name.lower() == parts[-1].lower()]
    if len(cands) > 1:
        def score(f):
            fp = [x.lower() for x in f.parts]
            n = 0
            for a, b in zip(reversed(fp), reversed([x.lower() for x in parts])):
                if a != b:
                    break
                n += 1
            return n
        best = max(score(f) for f in cands)
        cands = [f for f in cands if score(f) == best]
    if len(cands) == 1:
        return cands[0]
    if len(cands) > 1:
        raise SystemExit("ambiguous file '%s':\n  %s" % (spec, "\n  ".join(rel(c) for c in cands[:15])))
    return None


def grep(patterns, paths=None, only=None, fixed=True, word=False, ignore_case=False, exts=None):
    """Yield (path, line_no, text) for lines matching any pattern."""
    exts = exts or CODE_EXTS
    roots = [Path(x) for x in paths] if paths else [r["path"] for r in repos(only)]
    rg = shutil.which("rg")
    if rg:
        args = [rg, "-n", "--no-heading", "--with-filename", "--no-messages", "--max-columns", "400"]
        args += ["-F"] if fixed else []
        args += ["-w"] if word else []
        args += ["-i"] if ignore_case else []
        args += [f"-g=!{d}/" for d in SKIP_DIRS]
        args += [f"-g=*{e}" for e in sorted(exts)] + [f"-g=*{e.upper()}" for e in sorted(exts) if e.upper() != e]
        for pat in patterns:
            args += ["-e", pat]
        res = subprocess.run(args + [str(r) for r in roots], capture_output=True, text=True,
                             encoding="utf-8", errors="replace")
        for l in res.stdout.splitlines():
            m = re.match(r"^(.*?):(\d+):(.*)$", l)
            if m and not SKIP_FILE_RE.search(m.group(1)):
                yield Path(m.group(1)), int(m.group(2)), m.group(3)
        return
    flags = re.I if ignore_case else 0
    rx = re.compile("|".join((r"\b%s\b" if word else "%s") % (re.escape(p) if fixed else p) for p in patterns), flags)
    for root in roots:
        for f in ([root] if root.is_file() else [x for x in all_files(only) if str(x).startswith(str(root))]):
            if f.suffix.lower() not in exts:
                continue
            try:
                for i, line in enumerate(S.split_lines(S.read_text(f)), 1):
                    if rx.search(line):
                        yield f, i, line
            except OSError:
                continue


# ───────────── output budget ─────────────

class Budget:
    def __init__(self, total):
        self.total, self.used, self.skipped = total, 0, []

    def slice(self, p, sym=None, start=None, end=None, targets=(), mode="auto", max_lines=150, around=6, label=""):
        if sym:
            start, end = sym.doc_start, sym.end
        name = label or (sym.qname if sym else "")
        kind = f"[{sym.kind}] " if sym else ""
        if self.used >= self.total:
            self.skipped.append(f"{rel(p.path)}:{start}-{end} {name}")
            return False
        room = min(max_lines, max(self.total - self.used, 20))
        text, shown, total = S.render(p, start, end, targets, mode, room, around, sym)
        lines_out = text.count("\n") + 1
        self.used += lines_out
        note = f"{total} lines" + (f", {lines_out} shown" if lines_out < total else "")
        print(f"\n== {rel(p.path)}:{start}-{end}  {name}  {kind}({note})")
        print(text)
        return True

    def close(self):
        if self.skipped:
            print(f"\n-- budget reached ({self.total} lines); not shown:")
            for s in self.skipped[:30]:
                print("   " + s)
            if len(self.skipped) > 30:
                print(f"   … {len(self.skipped) - 30} more")


# ───────────── targets ─────────────

def parse_target(spec, only=None):
    """-> (path, Parsed, symbol or None, targets[], (start, end) or None)."""
    m = re.match(r"^(.*?)(?::(\d+(?:[-,]\d+)*))?$", spec) if not re.match(r"^[A-Za-z]:[\\/]", spec) else \
        re.match(r"^([A-Za-z]:.*?)(?::(\d+(?:[-,]\d+)*))?$", spec)
    file_part, nums = m.group(1), m.group(2)
    sym_name = None
    if "#" in file_part:
        file_part, sym_name = file_part.split("#", 1)
    path = resolve_file(file_part, only) if file_part and (nums or sym_name or Path(file_part).suffix) else None
    if path is None:
        if nums or sym_name:
            raise SystemExit(f"file not found: {file_part}")
        defs = find_defs(spec, only)
        if not defs:
            raise SystemExit(f"no definition found for '{spec}'")
        if len(defs) > 1:
            print(f"-- {len(defs)} definitions of {spec}; showing the first. Others:")
            for f, s in defs[1:8]:
                print(f"   {rel(f)}:{s.start}-{s.end} {s.qname}")
        f, s = defs[0]
        return f, S.parse(f), s, [], None
    p = S.parse(path)
    if sym_name:
        hits = S.by_name(p, sym_name)
        if not hits:
            raise SystemExit(f"{sym_name} not found in {rel(path)}")
        return path, p, hits[0], [], None
    if not nums:
        return path, p, None, [], (1, len(p.lines))
    if "-" in nums:
        a, b = (int(x) for x in nums.split("-")[:2])
        return path, p, None, list(range(a, b + 1)), (a, b)
    targets = [int(x) for x in nums.split(",")]
    return path, p, None, targets, None


def find_defs_many(names, only=None, paths=None, max_files=400):
    """One search for several names -> {name: [(file, symbol)]}, best match first."""
    bases = {n: n.split(".")[-1] for n in names}
    out = {n: [] for n in names}
    seen = set()
    for f, line, _ in grep(sorted(set(bases.values())), paths=paths, only=only, word=True):
        key = str(f.resolve())
        if key in seen or len(seen) >= max_files:
            continue
        seen.add(key)
        try:
            p = S.parse(f)
        except OSError:
            continue
        for n in names:
            out[n].extend((f, s) for s in S.by_name(p, n))
    for n in out:
        out[n].sort(key=lambda fs: (fs[1].kind == "callback",
                                    not fs[1].callable and fs[1].kind not in ("class", "interface"), len(str(fs[0]))))
    return out


def find_defs(name, only=None, paths=None):
    return find_defs_many([name], only, paths)[name]


# ───────────── commands ─────────────

def cmd_outline(a):
    rows = []
    for spec in a.paths:
        target = Path(spec) if Path(spec).exists() else ROOT / spec
        if target.is_dir():
            fl = sorted(f for f in target.rglob("*") if f.is_file() and f.suffix.lower() in CODE_EXTS
                        and not _skip(f.relative_to(target).parts) and not SKIP_FILE_RE.search(f.name))
            depth = a.depth if a.depth is not None else 0
        else:
            f = resolve_file(spec, a.repo)
            if not f:
                raise SystemExit(f"not found: {spec}")
            fl, depth = [f], a.depth if a.depth is not None else 3
        for f in fl:
            p = S.parse(f)
            syms = [s for s in p.symbols if s.depth <= depth and s.kind != "callback" or a.callbacks and s.depth <= depth]
            rows.append({"file": rel(f), "lines": len(p.lines), "lang": p.lang,
                         "symbols": [{"name": s.qname, "kind": s.kind, "start": s.start, "end": s.end, "depth": s.depth}
                                     for s in syms]})
            if a.json:
                continue
            print(f"{rel(f)}  ({len(p.lines)} lines, {p.lang})")
            for s in syms[: a.limit]:
                print(f"  {'  ' * s.depth}L{s.start}-{s.end} {s.kind} {s.name}"
                      + (f"  — {s.sig}" if a.sig else ""))
            if len(syms) > a.limit:
                print(f"  … {len(syms) - a.limit} more (--limit)")
    if a.json:
        print(json.dumps(rows, ensure_ascii=False, indent=1))


def cmd_show(a):
    b = Budget(a.budget)
    path, p, sym, targets, rng = parse_target(a.target, a.repo)
    mode = "full" if a.full else "around" if a.around is not None else "auto"
    around = a.around if a.around is not None else 6
    if sym:
        b.slice(p, sym, mode=mode, max_lines=a.max_lines, around=around)
    elif rng and not targets:
        b.slice(p, start=1, end=len(p.lines), mode=mode, max_lines=a.max_lines, label="(whole file)")
    else:
        groups = OrderedDict()
        for t in targets:
            s = S.enclosing(p, t, "outer" if a.outer else "callable", a.level)
            groups.setdefault(s, []).append(t)
        for s, ts in groups.items():
            if s and not a.range_only:
                b.slice(p, s, targets=ts, mode=mode, max_lines=a.max_lines, around=around)
            else:
                lo, hi = (rng if rng else (min(ts) - around, max(ts) + around))
                b.slice(p, start=max(1, lo), end=min(len(p.lines), hi), targets=ts, mode="full",
                        label=(s.qname if s else "(top level)"))
    b.close()


def cmd_find(a):
    defs = find_defs(a.name, a.repo, a.within)
    if a.json:
        print(json.dumps([{"file": rel(f), "start": s.start, "end": s.end, "name": s.qname, "kind": s.kind,
                           "sig": s.sig} for f, s in defs], ensure_ascii=False, indent=1))
        return
    if not defs:
        print(f"no definition of {a.name}")
        return 1
    for f, s in defs[: a.limit]:
        print(f"{rel(f)}:{s.start}-{s.end}  {s.kind} {s.qname}  — {s.sig}")
    if a.show:
        b = Budget(a.budget)
        for f, s in defs[: a.show]:
            b.slice(S.parse(f), s, max_lines=a.max_lines)
        b.close()


def cmd_refs(a):
    pats = a.names
    hits = list(grep(pats, paths=a.within, only=a.repo, fixed=not a.regex, word=not a.regex and not a.substring,
                     ignore_case=a.ignore_case))
    by_file = OrderedDict()
    for f, line, text in hits:
        by_file.setdefault(f, []).append((line, text))
    rows = []
    for f, items in by_file.items():
        try:
            p = S.parse(f)
        except OSError:
            continue
        groups = OrderedDict()
        for line, text in items:
            s = S.enclosing(p, line, "callable")
            is_def = bool(s and s.start <= line <= s.start + 1 and any(n.split(".")[-1] == s.name for n in pats))
            src = p.lines[line - 1] if line <= len(p.lines) else text
            groups.setdefault(S.label_at(p, line), []).append((line, src.strip(), is_def))
        rows.append((f, groups))
    if a.json:
        print(json.dumps([{"file": rel(f), "hits": [{"symbol": s, "line": l, "text": t, "def": d}
                                                    for s, ls in g.items() for l, t, d in ls]} for f, g in rows],
                         ensure_ascii=False, indent=1))
        return
    n_sym = sum(len(g) for _, g in rows)
    print(f"# {len(hits)} hit(s) of {', '.join(pats)} in {len(rows)} file(s), {n_sym} enclosing symbol(s)")
    shown = 0
    for f, groups in rows:
        if shown >= a.limit:
            print(f"… {len(rows) - shown} more file(s) (--limit)")
            break
        shown += 1
        print(f"\n{rel(f)}")
        for label, ls in groups.items():
            first = ls[: a.per_symbol]
            print(f"  {label}  " + ", ".join(f"L{l}{' (def)' if d else ''}" for l, _, d in ls))
            for l, t, _ in first:
                print(f"     {l}: {S.clip(t, 160)}")
            if len(ls) > a.per_symbol:
                print(f"     … +{len(ls) - a.per_symbol}")


IMPORT_RE = re.compile(r"import\s+(?:type\s+)?(?:([\w$]+)\s*,?\s*)?(?:\*\s+as\s+[\w$]+\s*)?(?:\{([^}]*)\})?\s*from\s*['\"]([^'\"]+)['\"]", re.S)


_TSCONF = {}


def _load_jsonc(path):
    t = S.read_text(path)
    t = re.sub(r'("(?:\\.|[^"\\])*")|//[^\n]*|/\*.*?\*/', lambda m: m.group(1) or "", t, flags=re.S)
    return json.loads(re.sub(r",(\s*[}\]])", r"\1", t))


def ts_aliases(start_dir):
    """[(alias_prefix, [target_dirs])] and baseUrl from the nearest tsconfig/jsconfig (follows `extends`)."""
    d = Path(start_dir)
    r = repo_of(d)
    stop = r["path"].resolve() if r else ROOT.resolve()
    while True:
        if str(d) in _TSCONF:
            return _TSCONF[str(d)]
        cands = [d / n for n in ("tsconfig.json", "jsconfig.json", "tsconfig.base.json", "tsconfig.paths.json")]
        found = [c for c in cands if c.is_file()]
        if found or d.resolve() == stop or d.parent == d:
            break
        d = d.parent
    aliases, base = [], None
    todo, seen = list(found), set()
    while todo:
        cf = todo.pop(0)
        if str(cf) in seen:
            continue
        seen.add(str(cf))
        try:
            conf = _load_jsonc(cf)
        except Exception:
            continue
        co = conf.get("compilerOptions", {})
        b = (cf.parent / co["baseUrl"]) if "baseUrl" in co else None
        base = base or b
        for k, vals in (co.get("paths") or {}).items():
            root = b or base or cf.parent
            aliases.append((k.rstrip("*"), [root / v.rstrip("*") for v in vals]))
        ext = conf.get("extends")
        if isinstance(ext, str) and ext.startswith("."):
            e = (cf.parent / ext)
            todo.append(e if e.suffix == ".json" else Path(str(e) + ".json"))
    _TSCONF[str(d)] = (aliases, base)
    return aliases, base


def _with_ext(cand):
    for ext in ("", ".ts", ".tsx", ".js", ".jsx", "/index.ts", "/index.tsx", "/index.js"):
        c = Path(str(cand) + ext)
        if c.is_file():
            return c
    return None


def ts_import_file(p, name):
    text = "\n".join(p.lines[:600])
    for m in IMPORT_RE.finditer(text):
        names = {m.group(1)} if m.group(1) else set()
        if m.group(2):
            for part in m.group(2).split(","):
                part = part.strip().replace("type ", "")
                if part:
                    names.add(part.split(" as ")[-1].strip())
        if name not in names:
            continue
        spec = m.group(3)
        here = Path(p.path).parent
        if spec.startswith("."):
            return _with_ext(here / spec)
        aliases, base = ts_aliases(here)
        for prefix, targets in sorted(aliases, key=lambda a: -len(a[0])):
            if spec.startswith(prefix) and prefix:
                for t in targets:
                    hit = _with_ext(t / spec[len(prefix):]) if spec[len(prefix):] else _with_ext(t)
                    if hit:
                        return hit
        if base:
            hit = _with_ext(base / spec)
            if hit:
                return hit
        r = repo_of(p.path)
        if r:
            return _with_ext(r["path"] / "src" / re.sub(r"^[@~]/", "", spec))
    return None


def resolve_local(p, name, recv=None):
    local = [s for s in S.by_name(p, name) if s.callable and s.kind != "callback"]
    if local and recv in (None, "this", "self", "base", "super"):
        return (Path(p.path), local[0]), "same file"
    if p.lang in ("typescript", "tsx", "javascript"):
        f = ts_import_file(p, recv or name)
        if f:
            q = S.parse(f)
            c = [s for s in S.by_name(q, name) if s.callable] or S.by_name(q, name)
            if c:
                return (f, c[0]), "import"
    return None, None


def cmd_flow(a):
    b = Budget(a.budget)
    path, p, sym, targets, _ = parse_target(a.target, a.repo)
    if sym is None:
        sym = S.enclosing(p, targets[0], "outer" if a.outer else "callable") if targets else None
    if sym is None:
        raise SystemExit("no enclosing function at that location")
    r = repo_of(path)
    rname = r["name"] if r else None
    seen = {(str(path), sym.start)}
    b.slice(p, sym, targets=targets, max_lines=a.max_lines)
    unresolved, ambiguous = set(), {}
    frontier = [(p, sym)]
    for depth in range(a.depth):
        nxt, found, pending = [], [], OrderedDict()
        for fp, fs in frontier:
            for line, name, recv in fp.calls:
                if not (fs.start <= line <= fs.end) or name in STOP_CALLS or name == fs.name:
                    continue
                hit, how = resolve_local(fp, name, recv)
                if hit:
                    found.append((hit, how, fp, line))
                elif name not in pending:
                    pending[name] = (fp, line)
        if pending:
            many = find_defs_many(list(pending), [rname] if rname else None, a.within)
            for name, (fp, line) in pending.items():
                defs = [(f, s) for f, s in many[name] if s.callable and s.kind != "callback"]
                if len(defs) == 1:
                    found.append((defs[0], "repo", fp, line))
                elif defs:
                    ambiguous[name] = len(defs)
                else:
                    unresolved.add(name)
        for (f, s), how, fp, line in found:
            key = (str(Path(f).resolve()), s.start)
            if key in seen:
                continue
            seen.add(key)
            q = S.parse(f)
            b.slice(q, s, max_lines=a.callee_lines, label=f"{s.qname}  <- called at {rel(fp.path)}:{line} ({how})")
            nxt.append((q, s))
        frontier = nxt
    if a.up:
        frontier = [(p, sym)]
        for depth in range(a.up):
            nxt = []
            for fp, fs in frontier:
                for f, line, _ in grep([fs.name], paths=a.within, only=[rname] if rname else None, word=True):
                    q = S.parse(f)
                    caller = S.enclosing(q, line, "callable")
                    if not caller or (str(Path(f).resolve()), caller.start) in seen:
                        continue
                    if caller.start <= line <= caller.start + 1 and caller.name == fs.name:
                        continue
                    seen.add((str(Path(f).resolve()), caller.start))
                    b.slice(q, caller, targets=[line], mode="around", around=a.around,
                            label=f"{caller.qname}  -> calls {fs.name} (caller)")
                    nxt.append((q, caller))
            frontier = nxt
    if unresolved:
        print(f"\n-- not in the repos (library/framework or dynamic): {', '.join(sorted(unresolved)[:40])}")
    if ambiguous:
        print("-- several definitions, not expanded (use find NAME): "
              + ", ".join(f"{n}×{c}" for n, c in sorted(ambiguous.items())[:30]))
    b.close()


FRAME_RES = [
    ("java", re.compile(r"at\s+(?P<qual>[\w$.<>]+)\((?P<file>[\w$]+\.(?:java|kt|scala|groovy)):(?P<line>\d+)\)")),
    ("dotnet", re.compile(r"(?:at|場所)\s+(?P<qual>\S+?)(?:\(.*?\))?\s+(?:in|場所)\s+(?P<path>.+?):(?:line|行)\s*(?P<line>\d+)")),
    ("python", re.compile(r'File "(?P<path>[^"]+)", line (?P<line>\d+)(?:, in (?P<qual>\S+))?')),
    ("js", re.compile(r"at\s+(?:(?P<qual>[^\s(]+)\s+)?\(?(?P<path>(?:[A-Za-z]:)?[^():\s]+\.[A-Za-z]{1,4}):(?P<line>\d+)(?::\d+)?\)?")),
    ("generic", re.compile(r"(?P<path>(?:[A-Za-z]:)?[\w./\\@-]+\.(?:tsx?|jsx?|java|cs|py|sql|vb|kt|go|php)):(?:line\s*)?(?P<line>\d+)")),
]


def frames(text):
    out = []
    for raw in text.splitlines():
        for kind, rx in FRAME_RES:
            m = rx.search(raw)
            if not m:
                continue
            d = m.groupdict()
            if kind == "java":
                pkg = d["qual"].rsplit(".", 2)[0].split("$")[0].replace(".", "/")
                d["path"] = f"{pkg}/{d['file']}"
            out.append((d["path"], int(d["line"]), d.get("qual"), raw.strip()))
            break
    return out


def cmd_trace(a):
    text = sys.stdin.read() if a.source in (None, "-") else S.read_text(a.source)
    fr = frames(text)
    if not fr:
        print("no stack frames or file:line references found")
        return 1
    b = Budget(a.budget)
    seen, outside, first = set(), [], True
    for path, line, qual, raw in fr:
        clean = re.sub(r"^(webpack|file):/+(\./)?", "", path).split("?")[0]
        try:
            f = resolve_file(clean, a.repo)
        except SystemExit as e:
            outside.append(f"{clean}:{line} (ambiguous)")
            continue
        if not f:
            outside.append(f"{clean}:{line}")
            continue
        p = S.parse(f)
        if line > len(p.lines):
            outside.append(f"{rel(f)}:{line} (beyond end of file — build/source mismatch? check the deployed version)")
            continue
        s = S.enclosing(p, line, "callable")
        key = (str(f), s.start if s else line)
        if key in seen or len(seen) >= a.max_frames:
            continue
        seen.add(key)
        label = (s.qname if s else "(top level)") + ("  [innermost repo frame]" if first else "  [caller]")
        if s:
            b.slice(p, s, targets=[line], mode="auto" if first else "around", max_lines=a.max_lines,
                    around=a.around, label=label)
        else:
            b.slice(p, start=max(1, line - a.around), end=min(len(p.lines), line + a.around), targets=[line],
                    mode="full", label=label)
        first = False
    if outside:
        uniq = list(OrderedDict.fromkeys(outside))
        print(f"\n-- {len(uniq)} frame(s) outside the registered repos (library, minified bundle → modules/log-triage symbolicate):")
        for o in uniq[:12]:
            print("   " + o)
    b.close()


def name_variants(name):
    words = [w.lower() for w in re.findall(r"[A-Z]+(?=[A-Z][a-z]|\d|\b|_)|[A-Z]?[a-z]+|\d+|[A-Z]+", name)] or [name.lower()]
    camel = words[0] + "".join(w.capitalize() for w in words[1:])
    return list(OrderedDict.fromkeys([name, camel, camel[:1].upper() + camel[1:], "_".join(words),
                                      "_".join(words).upper(), "-".join(words)]))


def layer_of(path, repo):
    n = path.name.lower()
    role = repo["role"] if repo else "other"
    inside = Path(path).resolve().relative_to(repo["path"].resolve()).as_posix().lower() if repo else n
    if re.search(r"(\.|_|-)(test|spec)\.|(^|/)(tests?|__tests__|spec)/", inside):
        return f"{role} · test"
    if path.suffix.lower() in S.SQL_EXTS:
        return f"{role} · sql"
    for kw, lab in (("controller", "controller"), ("service", "service"), ("repositor", "repository"),
                    ("dao", "repository"), ("mapper", "repository"), ("store", "state"), ("slice", "state"),
                    ("hook", "hook"), ("schema", "validation"), ("valid", "validation"), ("api", "api-client"),
                    ("designer", "ui-layout"), ("form", "ui"), ("page", "ui"), ("view", "ui"), ("dto", "model"),
                    ("model", "model"), ("entity", "model"), ("type", "types")):
        if kw in n:
            return f"{role} · {lab}"
    return f"{role} · {'ui' if n.endswith(('.tsx', '.jsx', '.vue')) else 'source'}"


def cmd_field(a):
    pats = []
    for n in a.names:
        pats.extend([n] if a.exact else name_variants(n))
    pats = list(OrderedDict.fromkeys(pats + (a.alias or [])))
    hits = list(grep(pats, paths=a.scope, only=a.repo, word=a.word, ignore_case=a.ignore_case))
    tree = defaultdict(OrderedDict)
    for f, line, _ in hits:
        tree[layer_of(f, repo_of(f))].setdefault(f, []).append(line)
    n_files = sum(len(v) for v in tree.values())
    print(f"# {', '.join(a.names)} — {len(hits)} hit(s) in {n_files} file(s); matched: {', '.join(pats)}")
    print("\n# by layer (hits / functions)")
    parsed = {}
    for layer in sorted(tree):
        print(f"## {layer}")
        for f, lines in tree[layer].items():
            p = parsed[f] = S.parse(f)
            funcs = {S.label_at(p, l) for l in lines}
            print(f"   {rel(f)}  {len(lines)} / {len(funcs)}")
    out_json, slices, used = [], [], 0
    print("\n# where (first hit text per function)")
    for layer in sorted(tree):
        for f, lines in tree[layer].items():
            p = parsed[f]
            groups = OrderedDict()
            for l in lines:
                groups.setdefault(S.label_at(p, l), []).append(l)
            for label, ls in groups.items():
                s = S.enclosing(p, ls[0], "callable")
                slices.append((p, s, ls))
                out_json.append({"layer": layer, "file": rel(f), "symbol": label, "lines": ls})
            if used >= a.budget:
                continue
            print(f"{rel(f)}")
            used += 1
            for label, ls in list(groups.items())[: a.per_file]:
                txt = S.clip(p.lines[ls[0] - 1].strip(), 140) if ls[0] <= len(p.lines) else ""
                more = f" +{len(ls) - 1}" if len(ls) > 1 else ""
                print(f"   {label}  L{ls[0]}{more}: {txt}")
                used += 1
            if len(groups) > a.per_file:
                print(f"   … {len(groups) - a.per_file} more function(s) (--per-file)")
                used += 1
    if used >= a.budget:
        print(f"-- listing cut at --budget {a.budget} lines; narrow with --scope or --repo")
    if a.json:
        print(json.dumps(out_json, ensure_ascii=False, indent=1))
    if a.show:
        b = Budget(a.budget)
        print("\n# reference slices (hit lines marked '>'; unrelated code folded)")
        for p, s, ls in slices:
            if s:
                b.slice(p, s, targets=ls, mode="around", around=a.around, max_lines=a.max_lines)
            else:
                b.slice(p, start=max(1, min(ls) - a.around), end=min(len(p.lines), max(ls) + a.around),
                        targets=ls, mode="around", around=a.around, label="(top level)")
        b.close()


def _decode(raw):
    for enc in ("utf-8-sig", "cp932", "cp1252"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1")


def cmd_diff(a):
    r = next((x for x in repos() if x["name"] == a.repo_name), None)
    if not r:
        raise SystemExit(f"unknown repo {a.repo_name}; registered: {', '.join(x['name'] for x in repos())}")
    args = ["git", "-C", str(r["path"]), "diff", "--unified=0", "--no-color", "--no-ext-diff"]
    args += ["--staged"] if a.staged else []
    args += [a.base or ("HEAD" if not a.staged else "")] if (a.base or not a.staged) else []
    args += ["--"] + (a.paths or [])
    out = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
    changes, cur, deleted = OrderedDict(), None, []
    for line in out.splitlines():
        if line.startswith("+++ "):
            cur = None if line.endswith("/dev/null") else line[6:] if line.startswith("+++ b/") else line[4:]
            if cur:
                changes.setdefault(cur, [])
        elif line.startswith("--- ") and line.endswith("/dev/null"):
            pass
        elif line.startswith("diff --git"):
            m = re.search(r" b/(.+)$", line)
            cur = m.group(1) if m else None
        elif line.startswith("deleted file"):
            deleted.append(cur)
            cur = None
        elif line.startswith("@@") and cur:
            m = re.match(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", line)
            start, n = int(m.group(1)), int(m.group(2) or 1)
            changes[cur].extend(range(start, start + n) if n else [max(start, 1)])
    if not changes and not deleted:
        print("no changes")
        return
    b = Budget(a.budget)
    print(f"# {len(changes)} changed file(s) in {r['name']}" + (f", {len(deleted)} deleted" if deleted else ""))
    rev = re.split(r"\.\.\.?", a.base)[1] or "HEAD" if a.base and ".." in a.base else None
    for relp, lines in changes.items():
        f = r["path"] / relp
        if f.suffix.lower() not in CODE_EXTS:
            print(f"\n== {r['name']}/{relp}  (not code; {len(lines)} changed line(s))")
            continue
        if rev:
            raw = subprocess.run(["git", "-C", str(r["path"]), "show", f"{rev}:{relp}"], capture_output=True).stdout
            p = S.parse(f, text=_decode(raw), rev=rev)
        elif f.is_file():
            p = S.parse(f)
        else:
            print(f"\n== {r['name']}/{relp}  (not on disk)")
            continue
        groups = OrderedDict()
        for l in lines:
            groups.setdefault(S.enclosing(p, l, "callable"), []).append(l)
        for s, ls in groups.items():
            if s:
                b.slice(p, s, targets=ls, mode="around", around=a.around, max_lines=a.max_lines)
            else:
                b.slice(p, start=max(1, min(ls) - a.around), end=min(len(p.lines), max(ls) + a.around),
                        targets=ls, mode="around", around=a.around, label="(top level)")
    for d in deleted:
        print(f"\n== {r['name']}/{d}  (deleted)")
    untracked = [] if rev or a.no_untracked else subprocess.run(["git", "-C", str(r["path"]), "ls-files", "--others", "--exclude-standard"],
                               capture_output=True, text=True, encoding="utf-8", errors="replace").stdout.split()
    if untracked:
        print(f"\n-- untracked (not in the diff): {', '.join(untracked[:20])}")
    b.close()


def cmd_sql(a):
    sql_repos = [x["name"] for x in repos() if any(k in x["role"] for k in ("database", "schema", "db"))]
    only = a.repo or None
    b = Budget(a.budget)
    if a.column:
        hits = list(grep([a.column], paths=a.within, only=only, word=True, ignore_case=True, exts=S.SQL_EXTS | {".xml"}))
        print(f"# column {a.column}: {len(hits)} hit(s)")
        for f, line, text in hits[: a.limit]:
            p = S.parse(f)
            s = S.enclosing(p, line, "any")
            src = p.lines[line - 1] if line <= len(p.lines) else text
            print(f"{rel(f)}:{line}  {(s.kind + ' ' + s.qname) if s else ''}  | {S.clip(src.strip(), 150)}")
        if len(hits) > a.limit:
            print(f"… {len(hits) - a.limit} more (--limit)")
        return
    defs = []
    seen = set()
    for f, line, _ in grep([a.name], paths=a.within, only=only, word=True, ignore_case=True, exts=S.SQL_EXTS):
        if str(f) in seen:
            continue
        seen.add(str(f))
        p = S.parse(f)
        defs.extend((p, s) for s in S.by_name(p, a.name))
    defs.sort(key=lambda ps: (ps[1].kind.endswith(" decl"), ps[1].kind == "package",
                              repo_of(ps[0].path)["name"] not in sql_repos if repo_of(ps[0].path) else True))
    if not defs:
        print(f"no SQL object named {a.name}" + ("" if sql_repos else " (no database repo registered)"))
        return 1
    for p, s in defs[1:]:
        print(f"-- also: {rel(p.path)}:{s.start}-{s.end} {s.kind} {s.qname}")
    for p, s in defs[: a.show]:
        b.slice(p, s, max_lines=a.max_lines, mode="full" if a.full else "auto")
    b.close()


def cmd_json(a):
    f = resolve_file(a.file) or Path(a.file)
    text = S.read_text(f)
    if f.suffix.lower() in (".yml", ".yaml"):
        import yaml
        data = yaml.safe_load(text)
    else:
        data = json.loads(text)

    def walk(node, path):
        yield path, node
        if isinstance(node, dict):
            for k, v in node.items():
                yield from walk(v, path + [str(k)])
        elif isinstance(node, list):
            for i, v in enumerate(node):
                yield from walk(v, path + [str(i)])

    def short(v, n=a.width):
        s = json.dumps(v, ensure_ascii=False)
        return s if len(s) <= n else s[:n] + f"…[{len(s)} chars]"

    if a.find:
        rx = re.compile(a.find, re.I)
        n = 0
        for path, v in walk(data, []):
            key_hit = path and rx.search(path[-1])
            val_hit = not isinstance(v, (dict, list)) and rx.search(str(v))
            if key_hit or val_hit:
                print(f"{'.'.join(path)} = {short(v)}")
                n += 1
                if n >= a.limit:
                    print("… (--limit)")
                    break
        return
    node = data
    for k in (a.path.split(".") if a.path else []):
        node = node[int(k)] if isinstance(node, list) else node[k]
    if a.keys or (isinstance(node, (dict, list)) and len(json.dumps(node)) > a.width * 20 and not a.full):
        def outline(n, depth, ind):
            if depth > a.depth:
                return
            items = n.items() if isinstance(n, dict) else enumerate(n[:3]) if isinstance(n, list) else []
            for k, v in items:
                size = f"{{{len(v)}}}" if isinstance(v, dict) else f"[{len(v)}]" if isinstance(v, list) else short(v, 60)
                print(f"{ind}{k}: {size}")
                if isinstance(v, (dict, list)):
                    outline(v, depth + 1, ind + "  ")
            if isinstance(n, list) and len(n) > 3:
                print(f"{ind}… {len(n) - 3} more items")
        print(f"# {a.path or '(root)'} — outline (depth {a.depth}); --full prints it all")
        outline(node, 1, "")
    else:
        print(json.dumps(node, ensure_ascii=False, indent=1))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(sp, max_lines=150, budget=400):
        sp.add_argument("--max-lines", type=int, default=max_lines)
        sp.add_argument("--budget", type=int, default=budget)
        sp.add_argument("--repo", action="append", help="limit to this repo (repeatable)")
        return sp

    sp = common(sub.add_parser("outline"))
    sp.add_argument("paths", nargs="+")
    sp.add_argument("--depth", type=int)
    sp.add_argument("--sig", action="store_true")
    sp.add_argument("--callbacks", action="store_true")
    sp.add_argument("--limit", type=int, default=200)
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(fn=cmd_outline)

    sp = common(sub.add_parser("show"))
    sp.add_argument("target")
    sp.add_argument("--full", action="store_true")
    sp.add_argument("--around", type=int)
    sp.add_argument("--outer", action="store_true", help="outermost function instead of innermost")
    sp.add_argument("--level", type=int, default=0, help="0 = innermost function, 1 = its parent, …")
    sp.add_argument("--range-only", action="store_true")
    sp.set_defaults(fn=cmd_show)

    sp = common(sub.add_parser("find"))
    sp.add_argument("name")
    sp.add_argument("--in", dest="within", action="append")
    sp.add_argument("--show", type=int, nargs="?", const=1, default=0)
    sp.add_argument("--limit", type=int, default=20)
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(fn=cmd_find)

    sp = common(sub.add_parser("refs"))
    sp.add_argument("names", nargs="+")
    sp.add_argument("--in", dest="within", action="append")
    sp.add_argument("--regex", action="store_true")
    sp.add_argument("--substring", action="store_true")
    sp.add_argument("-i", "--ignore-case", action="store_true")
    sp.add_argument("--per-symbol", type=int, default=2)
    sp.add_argument("--limit", type=int, default=40)
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(fn=cmd_refs)

    sp = common(sub.add_parser("flow"), max_lines=120, budget=450)
    sp.add_argument("target")
    sp.add_argument("--depth", type=int, default=1)
    sp.add_argument("--up", type=int, default=0)
    sp.add_argument("--around", type=int, default=4)
    sp.add_argument("--callee-lines", type=int, default=60)
    sp.add_argument("--in", dest="within", action="append", help="limit the definition/caller search to these paths")
    sp.add_argument("--outer", action="store_true")
    sp.set_defaults(fn=cmd_flow)

    sp = common(sub.add_parser("trace"), max_lines=120)
    sp.add_argument("source", nargs="?")
    sp.add_argument("--max-frames", type=int, default=8)
    sp.add_argument("--around", type=int, default=6)
    sp.set_defaults(fn=cmd_trace)

    sp = common(sub.add_parser("field"), max_lines=80)
    sp.add_argument("names", nargs="+")
    sp.add_argument("--scope", action="append", help="folder/file to search (e.g. the reference screen)")
    sp.add_argument("--alias", action="append", help="extra literal to match (label text, legacy name)")
    sp.add_argument("--exact", action="store_true", help="no camel/snake/kebab variants")
    sp.add_argument("--word", action="store_true", help="whole-word matches only (default: substring, so txtOrderDate matches)")
    sp.add_argument("-i", "--ignore-case", action="store_true")
    sp.add_argument("--show", action="store_true", help="print folded slices of every enclosing function")
    sp.add_argument("--around", type=int, default=3)
    sp.add_argument("--per-file", type=int, default=8)
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(fn=cmd_field)

    sp = common(sub.add_parser("diff"), max_lines=80, budget=600)
    sp.add_argument("repo_name")
    sp.add_argument("base", nargs="?", help="commit/branch to compare the working tree with, or A..B / A...B for commits only")
    sp.add_argument("--no-untracked", action="store_true")
    sp.add_argument("--staged", action="store_true")
    sp.add_argument("--around", type=int, default=4)
    sp.add_argument("paths", nargs="*")
    sp.set_defaults(fn=cmd_diff)

    sp = common(sub.add_parser("sql"), max_lines=200)
    sp.add_argument("name", nargs="?")
    sp.add_argument("--column")
    sp.add_argument("--in", dest="within", action="append")
    sp.add_argument("--show", type=int, default=1)
    sp.add_argument("--full", action="store_true")
    sp.add_argument("--limit", type=int, default=40)
    sp.set_defaults(fn=cmd_sql)

    sp = sub.add_parser("json")
    sp.add_argument("file")
    sp.add_argument("--path")
    sp.add_argument("--find")
    sp.add_argument("--keys", action="store_true")
    sp.add_argument("--full", action="store_true")
    sp.add_argument("--depth", type=int, default=2)
    sp.add_argument("--width", type=int, default=200)
    sp.add_argument("--limit", type=int, default=60)
    sp.set_defaults(fn=cmd_json)

    a = ap.parse_args()
    if a.cmd == "sql" and not (a.name or a.column):
        ap.error("sql needs NAME or --column")
    if S._ts_parser is None and a.cmd in ("show", "flow", "trace", "field", "diff", "outline", "refs", "find"):
        print("-- note: tree-sitter not installed (pip install tree-sitter-language-pack); using the less precise fallback",
              file=sys.stderr)
    return a.fn(a) or 0


if __name__ == "__main__":
    sys.exit(main())
