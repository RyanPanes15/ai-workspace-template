#!/usr/bin/env python3
"""Area → file index across every registered repo, plus an optional call graph.

An *area* is whatever your project keys work on — a screen ID (ORD-C0100), a
feature folder, a module name. Configure how it is recognised in
workspace.config.json:

  "area_index": {
    "id_pattern": "(?P<id>[A-Z][a-z]{2}[CB]\\d{4})",   # optional: IDs embedded in filenames
    "normalize": "upper",                               # upper | lower | none
    "roles": {                                          # filename suffix → role (first match wins)
      ".controller.ts": "controller", ".service.ts": "service", ".store.ts": "store",
      ".model.ts": "model", "Form.tsx": "form", ".page.tsx": "page", ".tsx": "component"
    },
    "call_pattern": "(?P<id>[A-Z][a-z]{2}B\\d{4})",     # optional: references scanned in frontend files
    "skip_dirs": ["node_modules", "dist", "build", ".git"]
  }

Without id_pattern the area key is the filename stem minus the role suffix
(`order-list.store.ts` → `order-list`).

Usage:
  python modules/area-index/area_index.py build [--calls]
  python modules/area-index/area_index.py <AREA> [<AREA> ...] [--json]
  python modules/area-index/area_index.py --callers <AREA>
Index: _work/area-index.json (gitignored).
"""
import argparse
import datetime
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INDEX = ROOT / "_work" / "area-index.json"
DEFAULT_ROLES = {".controller.ts": "controller", ".service.ts": "service", ".repository.ts": "repository",
                 ".persister.ts": "persister", ".store.ts": "store", ".model.ts": "model", ".types.ts": "types",
                 ".schema.ts": "schema", ".routes.ts": "routes", ".test.ts": "test", ".spec.ts": "test",
                 ".test.tsx": "test", "Form.tsx": "form", "Frm.tsx": "form", ".page.tsx": "page", ".tsx": "component",
                 ".vue": "component", "Controller.java": "controller", "Service.java": "service",
                 "Repository.java": "repository", ".cs": "source", ".py": "source", ".sql": "sql"}


def cfg():
    p = ROOT / "workspace.config.json"
    c = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    return c, c.get("area_index", {})


def norm(s, mode):
    return s.upper() if mode == "upper" else s.lower() if mode == "lower" else s


def build(with_calls):
    c, ai = cfg()
    roles = ai.get("roles") or DEFAULT_ROLES
    idp = re.compile(ai["id_pattern"]) if ai.get("id_pattern") else None
    callp = re.compile(ai["call_pattern"]) if ai.get("call_pattern") else idp
    mode = ai.get("normalize", "upper" if idp else "lower")
    skip = set(ai.get("skip_dirs", ["node_modules", "dist", "build", ".git", "coverage", "bin", "obj"]))
    idx, calls = {}, {}
    for r in c.get("repos", []):
        base = Path(r["path"]) if Path(r["path"]).is_absolute() else ROOT / r["path"]
        if not base.exists():
            print(f"  skip {r['name']}: path missing")
            continue
        n = 0
        for dp, dn, fn in os.walk(base):
            dn[:] = [d for d in dn if d not in skip and not d.startswith(".")]
            for f in fn:
                role = next((v for k, v in roles.items() if f.endswith(k)), None)
                if not role:
                    continue
                if idp:
                    m = idp.search(f)
                    if not m:
                        continue
                    key = norm(m.group("id") if "id" in m.groupdict() else m.group(0), mode)
                else:
                    suffix = next(k for k in roles if f.endswith(k))
                    key = norm(f[: -len(suffix)] or f, mode)
                path = Path(dp, f)
                rel = path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else path.as_posix()
                idx.setdefault(key, {}).setdefault(r["name"], {}).setdefault(role, []).append(rel)
                n += 1
                if with_calls and callp and r.get("role") == "frontend":
                    try:
                        for m in callp.finditer(path.read_text(encoding="utf-8", errors="replace")):
                            k2 = norm(m.group("id") if "id" in m.groupdict() else m.group(0), mode)
                            if k2 != key:
                                calls.setdefault(key, set()).add(k2)
                    except OSError:
                        pass
        print(f"  {r['name']:<18} {n:>6} files")
    INDEX.parent.mkdir(parents=True, exist_ok=True)
    INDEX.write_text(json.dumps({"built_at": datetime.datetime.now().isoformat(timespec="seconds"),
                                 "with_calls": with_calls, "index": idx,
                                 "calls": {k: sorted(v) for k, v in calls.items()}}, ensure_ascii=False), encoding="utf-8")
    print(f"-- {len(idx)} areas → {INDEX.relative_to(ROOT)}")


def query(keys, as_json, callers_only):
    if not INDEX.exists():
        sys.exit("No index — run: python modules/area-index/area_index.py build")
    d = json.loads(INDEX.read_text(encoding="utf-8"))
    _, ai = cfg()
    mode = ai.get("normalize", "upper" if ai.get("id_pattern") else "lower")
    out = {}
    for k in keys:
        k = norm(k, mode)
        rec = {"files": d["index"].get(k, {}), "calls": d["calls"].get(k, []),
               "called_by": sorted(s for s, v in d["calls"].items() if k in v)}
        out[k] = rec
        if as_json:
            continue
        print(f"\n# {k}")
        if not callers_only:
            for repo, roles in rec["files"].items():
                for role, paths in roles.items():
                    for p in paths:
                        print(f"  {repo:<18} {role:<11} {p}")
            if not rec["files"]:
                print("  not indexed (check the key or rebuild)")
            if rec["calls"]:
                print("  calls: " + ", ".join(rec["calls"]))
        print("  called by: " + (", ".join(rec["called_by"]) or "—") + ("" if d["with_calls"] else "  (built without --calls)"))
    if as_json:
        print(json.dumps(out, ensure_ascii=False, indent=2))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("args", nargs="*")
    ap.add_argument("--calls", action="store_true")
    ap.add_argument("--callers", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    if a.args[:1] == ["build"]:
        return build(a.calls)
    if not a.args:
        ap.error("give 'build' or an area key")
    query(a.args, a.json, a.callers)


if __name__ == "__main__":
    main()
