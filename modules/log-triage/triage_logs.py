#!/usr/bin/env python3
"""Cluster errors in log files into distinct issues (stable fingerprints), apply the
whitelist, and compare with the previous run — the mechanical half of
workflows/log-triage.md.

Usage:
  python modules/log-triage/triage_logs.py _work/logs/api/error-2026-09-28.log
  python modules/log-triage/triage_logs.py "_work/logs/**/*.log" --channel server
  python modules/log-triage/triage_logs.py client.log --channel client --symbolicate-maps repos/web/dist
  python modules/log-triage/triage_logs.py logs/*.log --json --limit 50
  python modules/log-triage/triage_logs.py --list          # issues in the store, by count
  python modules/log-triage/triage_logs.py --mute <fp> --note "why"   # adds a whitelist entry by code/message

Config (workspace.config.json -> "log_triage", all optional):
  "event_start": "^\\\\d{4}-\\\\d{2}-\\\\d{2}[ T]\\\\d{2}:\\\\d{2}"   regex a new log event starts with
  "error_filter": "ERROR|Error|Exception|FATAL|Uncaught"            events kept (others ignored)
  "code_pattern": "\\\\b([A-Z]{1,4}\\\\d{3,5})\\\\b"                 first capture = error code
  "whitelist": "context/log-whitelist.json"

State: _work/log-triage/issues.json (first/last seen, total count, runs seen). Each
run labels issues NEW (never seen before), ONGOING (seen in an earlier run and now), or
QUIET (seen before, absent in this input — NOT proof it is fixed; confirm in code).
"""
import argparse
import datetime
import glob
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import fingerprint as fpmod  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "_work" / "log-triage" / "issues.json"
TS_RE = re.compile(r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(?::\d{2})?")


def cfg():
    p = ROOT / "workspace.config.json"
    c = json.loads(p.read_text(encoding="utf-8")).get("log_triage", {}) if p.exists() else {}
    return {"event_start": c.get("event_start", r"^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}|^\[\d{4}-\d{2}-\d{2}"),
            "error_filter": c.get("error_filter", r"ERROR|Error|Exception|FATAL|Uncaught|Traceback"),
            "code_pattern": c.get("code_pattern"),
            "whitelist": ROOT / c.get("whitelist", "context/log-whitelist.json")}


def events(text, start_rx):
    cur = []
    for line in text.splitlines():
        if start_rx.search(line) and cur:
            yield "\n".join(cur)
            cur = []
        cur.append(line)
    if cur:
        yield "\n".join(cur)


def symbolicate(text, maps):
    node = shutil.which("node")
    if not node:
        return text
    r = subprocess.run([node, str(Path(__file__).parent / "symbolicate.js"), "--maps", maps],
                       input=text, capture_output=True, text=True, encoding="utf-8")
    return r.stdout if r.returncode == 0 and r.stdout else text


def load_state():
    return json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {"runs": 0, "issues": {}}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("inputs", nargs="*", help="log files or globs")
    ap.add_argument("--channel", default="server", help="server | client | any label")
    ap.add_argument("--symbolicate-maps", help="dir with *.js.map of the deployed client build")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--limit", type=int, default=40)
    ap.add_argument("--no-state", action="store_true", help="don't read/update the issue store")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--mute")
    ap.add_argument("--note", default="")
    a = ap.parse_args()
    c = cfg()
    state = load_state()

    if a.list:
        rows = sorted(state["issues"].values(), key=lambda r: -r["count"])[: a.limit]
        for r in rows:
            print(f"{r['fingerprint']}  {r['count']:>6}  {r['last_seen'][:16]:<16}  {r['frame'][:40]:<40}  {r['message'][:90]}")
        return 0
    if a.mute:
        it = state["issues"].get(a.mute)
        if not it:
            sys.exit(f"fingerprint {a.mute} not in the store")
        wl = json.loads(c["whitelist"].read_text(encoding="utf-8")) if c["whitelist"].exists() else []
        entry = ({"match_by": "code", "pattern": it["code"]} if it["code"] else {"match_by": "message", "pattern": it["message"][:120]})
        entry.update({"scope": it.get("endpoint") or it.get("frame", ""), "note": a.note or "muted via --mute",
                      "added_date": datetime.date.today().isoformat()})
        wl.append(entry)
        c["whitelist"].parent.mkdir(parents=True, exist_ok=True)
        c["whitelist"].write_text(json.dumps(wl, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"whitelisted ({entry['match_by']}) scoped to '{entry['scope']}' → {c['whitelist'].relative_to(ROOT)}")
        return 0

    files = sorted({f for pat in a.inputs for f in (glob.glob(pat, recursive=True) or [pat]) if Path(f).is_file()})
    if not files:
        sys.exit("no input log files found")
    start_rx, err_rx = re.compile(c["event_start"]), re.compile(c["error_filter"])
    wl = fpmod.load_whitelist(c["whitelist"])
    now = datetime.datetime.now().isoformat(timespec="seconds")
    run = {}
    n_events = 0
    for f in files:
        text = Path(f).read_text(encoding="utf-8", errors="replace")
        if a.symbolicate_maps:
            text = symbolicate(text, a.symbolicate_maps)
        for ev in events(text, start_rx):
            if not err_rx.search(ev):
                continue
            n_events += 1
            info = fpmod.compute(ev, a.channel, c["code_pattern"])
            ts = (TS_RE.search(ev) or [None])[0] if TS_RE.search(ev) else None
            r = run.setdefault(info["fingerprint"], {**info, "count": 0, "first": ts, "last": ts,
                                                    "sample": ev[:1500], "files": set()})
            r["count"] += 1
            r["files"].add(Path(f).name)
            if ts:
                r["first"] = min(filter(None, [r["first"], ts]))
                r["last"] = max(filter(None, [r["last"], ts]))

    prev = state["issues"]
    rows = []
    for fp_, r in run.items():
        w = fpmod.whitelisted(r, wl)
        status = "WHITELISTED" if w else ("ONGOING" if fp_ in prev else "NEW")
        rows.append({**{k: v for k, v in r.items() if k != "files"}, "files": sorted(r["files"]), "status": status,
                     "whitelist_note": (w or {}).get("note", "")})
        if not a.no_state:
            s = prev.setdefault(fp_, {k: r[k] for k in ("fingerprint", "channel", "code", "frame", "endpoint", "message")}
                                | {"first_seen": r["first"] or now, "count": 0, "runs_seen": 0, "sample": r["sample"]})
            s["count"] += r["count"]
            s["runs_seen"] += 1
            s["last_seen"] = r["last"] or now
    quiet = [p for k, p in prev.items() if k not in run and a.channel == p.get("channel")]
    if not a.no_state:
        state["runs"] += 1
        state["last_run"] = now
        STATE.parent.mkdir(parents=True, exist_ok=True)
        STATE.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")

    order = {"NEW": 0, "ONGOING": 1, "WHITELISTED": 2}
    rows.sort(key=lambda r: (order[r["status"]], -r["count"]))
    if a.json:
        print(json.dumps({"events": n_events, "issues": rows[: a.limit], "quiet": quiet[: a.limit]}, ensure_ascii=False, indent=2))
        return 0
    counts = {s: sum(1 for r in rows if r["status"] == s) for s in order}
    print(f"# Log triage — {len(files)} file(s), {n_events} error events → {len(rows)} distinct issues "
          f"(NEW {counts['NEW']} · ONGOING {counts['ONGOING']} · WHITELISTED {counts['WHITELISTED']} · QUIET {len(quiet)})\n")
    print("| status | fp | count | first → last | code | top app frame | endpoint | message |")
    print("| --- | --- | --- | --- | --- | --- | --- | --- |")
    for r in rows[: a.limit]:
        span = f"{(r['first'] or '')[5:16]} → {(r['last'] or '')[5:16]}"
        print(f"| {r['status']} | `{r['fingerprint']}` | {r['count']} | {span} | {r['code']} | {r['frame']} | "
              f"{r['endpoint']} | {r['message'][:110].replace('|', '/')} |")
    if len(rows) > a.limit:
        print(f"\n… {len(rows) - a.limit} more (raise --limit or use --json)")
    if quiet:
        print(f"\nQUIET (seen in earlier runs, absent here — confirm in code before calling them fixed): "
              + ", ".join(f"`{q['fingerprint']}`" for q in quiet[:20]))
    print("\nSamples: --json, or the store at _work/log-triage/issues.json. Logs may contain customer data — keep them in _work/.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
