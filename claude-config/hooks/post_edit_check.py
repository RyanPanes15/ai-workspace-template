"""Syntax-check files right after the agent edits them (PostToolUse hook), or on demand.

Hook mode (Edit | Write | MultiEdit): reads the tool payload from stdin, checks the
edited file, and on failure exits 2 with the error on stderr — Claude Code feeds that
back to the model. Unknown file types and missing checkers are skipped silently.

CLI mode:
  python .claude/hooks/post_edit_check.py --all                 # every checkable file in the workspace (skips repos/, node_modules, _work)
  python .claude/hooks/post_edit_check.py --all repos/api/src   # a subtree
  python .claude/hooks/post_edit_check.py path/a.py path/b.json # specific files
Exit 0 = all good, 1 = at least one failure (usable as a pre-commit or cron first step).

Checks: .py (compile), .json (parse), .toml (tomllib, 3.11+), .yml/.yaml (PyYAML if
installed), .js/.mjs/.cjs (node --check if node is on PATH), .sh (bash -n if bash is on
PATH). Also flags a file that ends inside an unterminated triple-quoted string or with a
dangling open bracket — the usual truncation shapes.
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKIP_DIRS = {"node_modules", ".git", "_work", "repos", "__pycache__", "dist", "build", ".venv", "venv"}
EXTS = {".py", ".json", ".toml", ".yml", ".yaml", ".js", ".mjs", ".cjs", ".sh"}


def check(path: Path):
    """Return None if OK/unchecked, else an error string."""
    ext = path.suffix.lower()
    if ext not in EXTS or not path.is_file():
        return None
    try:
        text = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        return None  # legacy-encoded file; not ours to judge
    except OSError as e:
        return f"cannot read: {e}"
    try:
        if ext == ".py":
            compile(text, str(path), "exec")
        elif ext == ".json":
            if text.strip():
                json.loads(text)
        elif ext == ".toml":
            try:
                import tomllib
            except ImportError:
                return None
            tomllib.loads(text)
        elif ext in (".yml", ".yaml"):
            try:
                import yaml
            except ImportError:
                return None
            list(yaml.safe_load_all(text))
        elif ext in (".js", ".mjs", ".cjs"):
            node = shutil.which("node")
            if not node:
                return None
            r = subprocess.run([node, "--check", str(path)], capture_output=True, text=True, timeout=20)
            if r.returncode:
                out = (r.stderr or r.stdout or "").splitlines()
                hit = [l for l in out if "Error" in l] or out[:1]
                loc = next((l.strip() for l in out if l.strip().startswith(str(path)) or ":" in l[:len(str(path)) + 8]), "")
                return f"{hit[0].strip() if hit else 'node --check failed'} {loc}".strip()
        elif ext == ".sh":
            bash = shutil.which("bash")
            if not bash:
                return None
            r = subprocess.run([bash, "-n", str(path)], capture_output=True, text=True, timeout=20)
            if r.returncode:
                return r.stderr.strip() or "bash -n failed"
    except SyntaxError as e:
        lines = text.count("\n") + 1
        tail = e.lineno and lines > 50 and e.lineno >= lines - 2
        return f"SyntaxError line {e.lineno}: {e.msg}" + (" — error is at the END of the file: it may have been TRUNCATED by the edit" if tail else "")
    except json.JSONDecodeError as e:
        return f"JSON error line {e.lineno} col {e.colno}: {e.msg}"
    except Exception as e:  # tomllib / yaml errors
        return f"{type(e).__name__}: {e}"
    return None


def mistakes_index_gap(path: Path):
    """A new/edited mistakes/<class>.md must be listed in mistakes/INDEX.md (AGENTS.md §10)."""
    try:
        rel = path.resolve().relative_to((ROOT / "mistakes").resolve())
    except ValueError:
        return None
    if rel.suffix != ".md" or rel.name in ("INDEX.md", "README.md", "_TEMPLATE.md") or len(rel.parts) > 1:
        return None
    index = ROOT / "mistakes" / "INDEX.md"
    if index.exists() and f"({rel.name})" not in index.read_text(encoding="utf-8"):
        return f"mistakes/{rel.name} is not listed in mistakes/INDEX.md — add its line (file · severity · triggers)"
    return None


def iter_files(targets):
    for t in targets:
        p = Path(t)
        p = p if p.is_absolute() else ROOT / p
        if p.is_file():
            yield p
            continue
        for dp, dn, fn in os.walk(p):
            dn[:] = [d for d in dn if d not in SKIP_DIRS and not d.startswith(".")]
            for f in fn:
                if Path(f).suffix.lower() in EXTS:
                    yield Path(dp, f)


def hook():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    ti = data.get("tool_input") or {}
    fp = ti.get("file_path") or ti.get("notebook_path")
    if not fp:
        return 0
    err = check(Path(fp))
    if err:
        print(f"post-edit check FAILED for {fp}: {err}\n"
              "Re-read the whole file and repair it before continuing (a large edit may have been truncated).",
              file=sys.stderr)
        return 2
    gap = mistakes_index_gap(Path(fp))
    if gap:
        print(f"mistake log: {gap}", file=sys.stderr)
        return 2
    return 0


def cli(args):
    targets = [a for a in args if a != "--all"] or ([str(ROOT)] if "--all" in args else [])
    if not targets:
        print(__doc__)
        return 0
    bad = n = 0
    for f in iter_files(targets):
        n += 1
        err = check(f)
        if err:
            bad += 1
            try:
                shown = f.relative_to(ROOT)
            except ValueError:
                shown = f
            print(f"FAIL {shown}: {err}")
    print(f"-- checked {n} file(s), {bad} failure(s)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(cli(sys.argv[1:]) if len(sys.argv) > 1 else hook())
