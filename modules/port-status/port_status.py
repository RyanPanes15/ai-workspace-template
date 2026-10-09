#!/usr/bin/env python3
"""Progress and consistency of a port, from context/projects/<project>/port-map.csv.

  python modules/port-status/port_status.py                 # progress summary
  python modules/port-status/port_status.py --check         # validate rows and paths (exit 1 on problems)
  python modules/port-status/port_status.py --discover      # reference areas with no row (needs area-index)
  python modules/port-status/port_status.py --set ORD-C0100 verified --inventory _work/runs/ORD-C0100/inventory.md
  python modules/port-status/port_status.py --add ORD-C0100 --ref "legacy/OrderFrm.cs;legacy/OrderAction.java"
  add --project <name> when the workspace has more than one port project.

port-map.csv columns: area, reference_paths, new_paths, status, inventory, notes.
Paths are `;`-separated and relative to the workspace root. Lines starting with # are skipped.
Statuses: not-started · inventoried · in-progress · verified · done · deferred.
`verified` and `done` require an inventory file (the logic inventory the completeness
verifier checked).
"""
import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MAP = None
FIELDS = ["area", "reference_paths", "new_paths", "status", "inventory", "notes"]
STATUSES = ["not-started", "inventoried", "in-progress", "verified", "done", "deferred"]


def pick_project(name):
    """The named project, or the only port project when no name is given."""
    cfg = json.loads((ROOT / "workspace.config.json").read_text(encoding="utf-8"))
    projects = cfg.get("projects", [])
    match = [p for p in projects if (p["name"] == name if name else "port" in p.get("types", []))]
    if len(match) != 1:
        sys.exit(f"pass --project <name> (port projects: "
                 f"{', '.join(p['name'] for p in projects if 'port' in p.get('types', [])) or 'none'})")
    return cfg, match[0]


def load():
    if not MAP.exists():
        sys.exit(f"{MAP.relative_to(ROOT).as_posix()} not found — run setup with the port profile, or create it with the header:\n"
                 + ",".join(FIELDS))
    lines = [l for l in MAP.read_text(encoding="utf-8-sig").splitlines() if l.strip() and not l.startswith("#")]
    return list(csv.DictReader(lines))


def save(rows):
    header = "# status: " + " | ".join(STATUSES) + "\n"
    with MAP.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        f.write(header)
        for r in rows:
            w.writerow({k: r.get(k, "") for k in FIELDS})


def paths(cell):
    return [p.strip() for p in (cell or "").split(";") if p.strip()]


def summary(rows):
    total = len(rows)
    counts = {s: sum(1 for r in rows if r["status"] == s) for s in STATUSES}
    active = total - counts["deferred"]
    finished = counts["verified"] + counts["done"]
    pct = 100 * finished / active if active else 0
    print(f"# Port status — {total} areas, {finished}/{active} verified or done ({pct:.0f}%)\n")
    for s in STATUSES:
        print(f"  {s:<12} {counts[s]:>5}")
    stuck = [r["area"] for r in rows if r["status"] == "in-progress"]
    if stuck:
        print(f"\nIn progress: {', '.join(stuck[:30])}")


def check(rows):
    problems = []
    seen = set()
    for r in rows:
        a = r["area"]
        if a in seen:
            problems.append(f"{a}: duplicate row")
        seen.add(a)
        if r["status"] not in STATUSES:
            problems.append(f"{a}: unknown status '{r['status']}'")
        for p in paths(r["reference_paths"]):
            if not (ROOT / p).exists():
                problems.append(f"{a}: reference path missing: {p}")
        if r["status"] in ("in-progress", "verified", "done") and not paths(r["new_paths"]):
            problems.append(f"{a}: status {r['status']} but no new_paths")
        for p in paths(r["new_paths"]):
            if not (ROOT / p).exists():
                problems.append(f"{a}: new path missing: {p}")
        if r["status"] in ("verified", "done"):
            inv = r.get("inventory", "").strip()
            if not inv or not (ROOT / inv).exists():
                problems.append(f"{a}: status {r['status']} without an existing inventory file")
    for p in problems:
        print("PROBLEM", p)
    print(f"-- {len(rows)} rows, {len(problems)} problem(s)")
    return 1 if problems else 0


def discover(rows, cfg, project):
    idx = ROOT / "_work" / "area-index.json"
    if not idx.exists():
        sys.exit("No area index — run: python modules/area-index/area_index.py build")
    ref_repos = {r["name"] for r in cfg.get("repos", [])
                 if r["name"] in project.get("repos", []) and str(r.get("role", "")).startswith("legacy")}
    ref_repos |= set(project.get("reference_repos", []))
    index = json.loads(idx.read_text(encoding="utf-8"))["index"]
    mapped = {r["area"].upper() for r in rows}
    missing = sorted(a for a, repos in index.items() if set(repos) & ref_repos and a.upper() not in mapped)
    for a in missing:
        print(f"UNMAPPED {a}  ({', '.join(sorted(set(index[a]) & ref_repos))})")
    print(f"-- {len(missing)} reference area(s) without a port-map row")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--discover", action="store_true")
    ap.add_argument("--set", nargs=2, metavar=("AREA", "STATUS"))
    ap.add_argument("--add", metavar="AREA")
    ap.add_argument("--ref", default="")
    ap.add_argument("--new", default="")
    ap.add_argument("--inventory", default=None)
    ap.add_argument("--note", default=None)
    ap.add_argument("--project", help="port project (default: the only one)")
    a = ap.parse_args()
    global MAP
    cfg, project = pick_project(a.project)
    MAP = ROOT / "context" / "projects" / project["name"] / "port-map.csv"
    rows = load()
    if a.add:
        if any(r["area"] == a.add for r in rows):
            sys.exit(f"{a.add} already mapped")
        rows.append({"area": a.add, "reference_paths": a.ref, "new_paths": a.new, "status": "not-started",
                     "inventory": a.inventory or "", "notes": a.note or ""})
        save(rows)
        print(f"added {a.add}")
        return 0
    if a.set:
        area, status = a.set
        if status not in STATUSES:
            sys.exit(f"status must be one of {', '.join(STATUSES)}")
        row = next((r for r in rows if r["area"] == area), None)
        if not row:
            sys.exit(f"{area} not in port-map.csv (use --add)")
        row["status"] = status
        if a.inventory is not None:
            row["inventory"] = a.inventory
        if a.new:
            row["new_paths"] = a.new
        if a.note is not None:
            row["notes"] = a.note
        inv = row.get("inventory", "").strip()
        if status in ("verified", "done") and not (inv and (ROOT / inv).exists()):
            sys.exit(f"{area}: {status} needs an existing inventory file (--inventory PATH); not saved")
        save(rows)
        print(f"{area} → {status}")
        return check([row])
    if a.check:
        return check(rows)
    if a.discover:
        return discover(rows, cfg, project)
    summary(rows)
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
