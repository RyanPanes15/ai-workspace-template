#!/usr/bin/env python3
"""Fetch work items from the trackers declared in workspace.config.json and write
normalized JSON exports the workflows read (default: _work/items/<source>.json).

Usage:
  python modules/tracker/fetch_items.py            # all enabled sources (best-effort)
  python modules/tracker/fetch_items.py --source bugs
  python modules/tracker/fetch_items.py --get BUG-42   # print one item (routes by prefix)

Source types (workspace.config.json -> tracker.sources[]):
  csv    {"location": "path/to/export.csv"}
  json   {"location": "path/to/export.json", "records_key": "items"}
  gsheet {"location": "<spreadsheet id>", "worksheet": "Sheet1", "header_row": 1}
         needs `pip install gspread google-auth` and a service-account key at
         secrets/service-account.json shared (read-only) on the sheet
  github {"location": "owner/repo", "labels": "bug"}   uses the `gh` CLI
  redmine {"location": "https://redmine.example.com", "project": "my-project",
           "status": "*", "query_id": null}
         read-only REST (issues.json); API key from $REDMINE_API_KEY or
         secrets/redmine.json {"api_key": "..."}; custom fields flattened by name

Common keys: name, type, id_prefix ("" for bare numbers), id_field, field_map
({normalized_key: source_column}), output (optional path), enabled.
Every record gets: id (prefixed), source, plus mapped fields; unmapped columns are
kept under "raw".
"""
import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load_cfg():
    p = ROOT / "workspace.config.json"
    if not p.exists():
        sys.exit("workspace.config.json missing — run setup/setup_workspace.py first.")
    return json.loads(p.read_text(encoding="utf-8"))


def rows_for(src):
    t, loc = src["type"], src.get("location", "")
    if t == "csv":
        with open(ROOT / loc, encoding=src.get("encoding", "utf-8-sig"), newline="") as f:
            return list(csv.DictReader(f))
    if t == "json":
        data = json.loads((ROOT / loc).read_text(encoding="utf-8"))
        return data[src["records_key"]] if src.get("records_key") else data
    if t == "gsheet":
        import gspread
        gc = gspread.service_account(filename=str(ROOT / "secrets" / "service-account.json"))
        ws = gc.open_by_key(loc).worksheet(src.get("worksheet", "Sheet1"))
        vals = ws.get_all_values()
        h = src.get("header_row", 1) - 1
        header = vals[h]
        return [dict(zip(header, r)) for r in vals[h + 1:] if any(c.strip() for c in r)]
    if t == "github":
        cmd = ["gh", "issue", "list", "-R", loc, "--state", src.get("state", "all"), "--limit", str(src.get("limit", 500)),
               "--json", "number,title,body,labels,state,assignees,createdAt,closedAt,url"]
        if src.get("labels"):
            cmd += ["--label", src["labels"]]
        return json.loads(subprocess.check_output(cmd, text=True))
    if t == "redmine":
        return redmine_rows(src)
    raise ValueError(f"unknown source type {t}")


def redmine_rows(src):
    import os
    import urllib.parse
    import urllib.request
    key = os.environ.get("REDMINE_API_KEY")
    kp = ROOT / "secrets" / "redmine.json"
    if not key and kp.exists():
        key = json.loads(kp.read_text(encoding="utf-8")).get("api_key")
    if not key:
        raise RuntimeError("no Redmine API key ($REDMINE_API_KEY or secrets/redmine.json)")
    base = src["location"].rstrip("/")
    rows, offset = [], 0
    while True:
        q = {"limit": 100, "offset": offset, "status_id": src.get("status", "*"), "sort": "id"}
        if src.get("project"):
            q["project_id"] = src["project"]
        if src.get("query_id"):
            q["query_id"] = src["query_id"]
        req = urllib.request.Request(f"{base}/issues.json?{urllib.parse.urlencode(q)}",
                                     headers={"X-Redmine-API-Key": key, "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as r:
            page = json.loads(r.read().decode("utf-8"))
        for it in page.get("issues", []):
            row = {"id": it["id"], "subject": it.get("subject"), "description": it.get("description"),
                   "status": (it.get("status") or {}).get("name"), "tracker": (it.get("tracker") or {}).get("name"),
                   "priority": (it.get("priority") or {}).get("name"), "author": (it.get("author") or {}).get("name"),
                   "assigned_to": (it.get("assigned_to") or {}).get("name"), "created_on": it.get("created_on"),
                   "updated_on": it.get("updated_on"), "closed_on": it.get("closed_on"),
                   "url": f"{base}/issues/{it['id']}"}
            for cf in it.get("custom_fields", []):
                row[cf.get("name")] = cf.get("value")
            rows.append(row)
        offset += len(page.get("issues", []))
        if not page.get("issues") or offset >= page.get("total_count", 0):
            break
    return rows


def normalize(src, rows):
    fm = src.get("field_map", {})
    idf = src.get("id_field", "id" if src["type"] != "github" else "number")
    out = []
    for r in rows:
        rid = str(r.get(idf, "")).strip()
        if not rid:
            continue
        rec = {"id": f"{src.get('id_prefix', '')}{rid}", "source": src["name"]}
        used = {idf}
        for k, col in fm.items():
            rec[k] = r.get(col)
            used.add(col)
        rec["raw"] = {k: v for k, v in r.items() if k not in used}
        out.append(rec)
    return out


def out_path(src):
    return ROOT / src.get("output", f"_work/items/{src['name']}.json")


def fetch(src):
    items = normalize(src, rows_for(src))
    p = out_path(src)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    return len(items), p


def get(cfg, item_id):
    srcs = sorted(cfg.get("tracker", {}).get("sources", []), key=lambda s: -len(s.get("id_prefix", "")))
    for s in srcs:
        pre = s.get("id_prefix", "")
        if item_id.upper().startswith(pre.upper()) and (pre or item_id.isdigit()):
            p = out_path(s)
            if not p.exists():
                sys.exit(f"{p.relative_to(ROOT)} missing — run fetch first.")
            for it in json.loads(p.read_text(encoding="utf-8")):
                if it["id"].upper() == item_id.upper():
                    print(json.dumps(it, ensure_ascii=False, indent=1))
                    return
            sys.exit(f"{item_id} not found in {s['name']}")
    sys.exit(f"No source matches the prefix of {item_id} — ask which tracker it belongs to.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source")
    ap.add_argument("--get")
    a = ap.parse_args()
    cfg = load_cfg()
    if a.get:
        return get(cfg, a.get)
    srcs = [s for s in cfg.get("tracker", {}).get("sources", []) if s.get("enabled", True)]
    if a.source:
        srcs = [s for s in srcs if s["name"] == a.source]
    if not srcs:
        sys.exit("No tracker sources configured (workspace.config.json -> tracker.sources).")
    bad = 0
    for s in srcs:
        try:
            n, p = fetch(s)
            print(f"OK   {s['name']:<16} {n:>5} items -> {p.relative_to(ROOT)}")
        except Exception as e:  # best-effort: one failing source never blocks the rest
            bad += 1
            print(f"WARN {s['name']:<16} {type(e).__name__}: {e}")
    sys.exit(1 if bad == len(srcs) else 0)


if __name__ == "__main__":
    main()
