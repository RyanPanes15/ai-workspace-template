#!/usr/bin/env python3
"""Check the cross-workspace parity registry (docs/parity.md).

  python modules/parity/parity_check.py            # full report
  python modules/parity/parity_check.py --json
  python modules/parity/parity_check.py --registry path/to/parity.md

For each **byte-identical** row: hash every copy (CRLF→LF normalized) and report
mismatches or missing copies. For each **mirrored** row: extract the regex matches of
the `check` column from each copy and report differences. Then scan the `## Scan`
globs for files present at the same relative path in two or more workspaces that no
row mentions ("unregistered").

Exit: 0 clean · 1 byte-identical drift or missing copy · 2 registry/usage error.
Mirrored differences and unregistered pairs are reported but do not fail the run —
a human decides whether they are intentional.
"""
import argparse
import fnmatch
import hashlib
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKIP = {"node_modules", ".git", "_work", "__pycache__", "dist", "build", "repos"}


def tables(md):
    """{section_title_lower: [row dicts]} for every markdown table under a ## heading."""
    out, sec, header = {}, None, None
    for line in md.splitlines():
        if line.startswith("## "):
            sec, header = line[3:].strip().lower(), None
            out.setdefault(sec, [])
            continue
        if line.strip().startswith("<!--"):
            continue  # commented-out example rows don't break the table
        if not sec or not line.strip().startswith("|"):
            header = None
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if header is None:
            header = [c.lower() for c in cells]
        elif all(set(c) <= set("-: ") for c in cells):
            continue
        else:
            out[sec].append(dict(zip(header, cells)))
    return out


def scan_globs(md):
    m = re.search(r"## Scan.*?```\n(.*?)```", md, re.S)
    return [g.strip() for g in m.group(1).splitlines() if g.strip()] if m else []


def digest(p: Path):
    return hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest()[:16]


def files_under(p: Path):
    if p.is_file():
        return {"": p}
    res = {}
    for dp, dn, fn in os.walk(p):
        dn[:] = [d for d in dn if d not in SKIP]
        for f in fn:
            fp = Path(dp, f)
            res[fp.relative_to(p).as_posix()] = fp
    return res


def resolve(row, roots):
    """Return {workspace: Path} for a row."""
    path = row.get("path", "").strip("`")
    if "=" in path:
        out = {}
        for part in path.split("="):
            ws, rel = part.strip().strip("`").split(":", 1)
            out[ws.strip()] = roots[ws.strip()] / rel.strip()
        return out
    names = [w.strip() for w in row.get("workspaces", "").split(",") if w.strip()] or list(roots)
    return {w: roots[w] / path for w in names if w in roots}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--registry", default=str(ROOT / "docs" / "parity.md"))
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    md = Path(a.registry).read_text(encoding="utf-8")
    t = tables(md)
    roots = {}
    for r in t.get("workspaces", []):
        p = Path(r.get("root", ".").strip("`"))
        roots[r["name"]] = (p if p.is_absolute() else ROOT / p).resolve()
    if len(roots) < 2:
        print("Registry lists fewer than two workspaces — nothing to compare.")
        return 0
    missing_roots = [n for n, p in roots.items() if not p.exists()]
    report = {"drift": [], "missing": [], "mirrored": [], "unregistered": [], "ok": 0}
    listed = set()

    for row in t.get("byte-identical", []):
        if not row.get("path"):
            continue
        paths = resolve(row, roots)
        listed.update(p.resolve() for p in paths.values())
        views = {w: files_under(p) if p.exists() else None for w, p in paths.items()}
        for w, v in views.items():
            if v is None and w not in missing_roots:
                report["missing"].append(f"{row['path']} — absent in '{w}'")
        present = {w: v for w, v in views.items() if v}
        rels = set().union(*[set(v) for v in present.values()]) if present else set()
        for rel in sorted(rels):
            hashes = {w: (digest(v[rel]) if rel in v else "MISSING") for w, v in present.items()}
            label = row["path"] + (f"/{rel}" if rel else "")
            if len(set(hashes.values())) > 1:
                report["drift"].append({"path": label, "hashes": hashes, "source": row.get("source of truth", "")})
            else:
                report["ok"] += 1

    for row in t.get("mirrored", []):
        if not row.get("path"):
            continue
        paths = resolve(row, roots)
        listed.update(p.resolve() for p in paths.values())
        pat = row.get("check", "").strip("`")
        if not pat:
            continue
        rx = re.compile(pat)
        found = {}
        for w, p in paths.items():
            if p.is_file():
                found[w] = sorted(set(m.group(0) for m in rx.finditer(p.read_text(encoding="utf-8", errors="replace"))))
        if len({json.dumps(v) for v in found.values()}) > 1:
            base = set(next(iter(found.values())))
            diff = {w: {"only_here": sorted(set(v) - base), "missing_here": sorted(base - set(v))} for w, v in found.items()}
            report["mirrored"].append({"path": row["path"], "check": pat, "diff": diff})

    for sec in ("shared-name-only", "single source"):
        for row in t.get(sec, []):
            for p in resolve(row, roots).values():
                listed.add(p.resolve())

    globs = scan_globs(md)
    if globs:
        per_ws = {}
        for w, root in roots.items():
            if not root.exists():
                continue
            names = set()
            for dp, dn, fn in os.walk(root):
                dn[:] = [d for d in dn if d not in SKIP and not d.startswith(".") or d == ".claude"]
                for f in fn:
                    rel = Path(dp, f).relative_to(root).as_posix()
                    if any(fnmatch.fnmatch(rel, g) for g in globs):
                        names.add(rel)
            per_ws[w] = names
        common = {}
        for w, names in per_ws.items():
            for n in names:
                common.setdefault(n, []).append(w)
        for rel, ws in sorted(common.items()):
            if len(ws) > 1 and not any((roots[w] / rel).resolve() in listed or
                                       any(str((roots[w] / rel).resolve()).startswith(str(l) + os.sep) for l in listed)
                                       for w in ws):
                same = len({digest(roots[w] / rel) for w in ws}) == 1
                report["unregistered"].append(f"{rel} ({', '.join(ws)}; {'identical' if same else 'DIFFERENT'})")

    if a.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"# Parity check — {', '.join(f'{n}={p}' for n, p in roots.items())}\n")
        if missing_roots:
            print(f"WARN workspace root(s) not found: {', '.join(missing_roots)}\n")
        print(f"byte-identical OK: {report['ok']} · drift: {len(report['drift'])} · missing: {len(report['missing'])} · "
              f"mirrored diffs: {len(report['mirrored'])} · unregistered: {len(report['unregistered'])}\n")
        for d in report["drift"]:
            print(f"DRIFT   {d['path']}  " + "  ".join(f"{w}={h}" for w, h in d["hashes"].items())
                  + (f"  (source of truth: {d['source']})" if d["source"] else ""))
        for m in report["missing"]:
            print(f"MISSING {m}")
        for m in report["mirrored"]:
            print(f"MIRROR  {m['path']}  check /{m['check']}/  " + json.dumps(m["diff"], ensure_ascii=False))
        for u in report["unregistered"]:
            print(f"UNREG   {u}")
    return 1 if report["drift"] or report["missing"] else 0


if __name__ == "__main__":
    sys.exit(main())
