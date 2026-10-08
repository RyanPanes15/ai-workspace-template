#!/usr/bin/env python3
"""Stop hook: append one line per turn to reports/usage.jsonl.

Records session, workflow command, item id(s), tokens by type, model family,
estimated cost, and wall seconds, so you can see where effort goes per item and
audit model routing (actual vs intended tier).

Install: setup/setup_workspace.py adds it to .claude/settings.local.json when the
module is enabled. Then restart the agent (or open /hooks once).

CLI:
  python modules/usage-metrics/usage_tracker.py --report        # per-command totals + cache signals
  python modules/usage-metrics/usage_tracker.py --report --by model|item|user|session
  python modules/usage-metrics/usage_tracker.py --outcome <ID> pass|fail|open   # per-item verdict ($/pass)
  python modules/usage-metrics/usage_tracker.py --check         # heartbeat: is the hook actually recording?
  python modules/usage-metrics/usage_tracker.py --coverage --ledgers a.jsonl b.jsonl [--since 2026-09-01]
        # team roll-up: who in context/people.json has NO ledger lines (silent install failure)

Each line carries `user` (git user.email, or $USAGE_USER), canonicalised through
context/people.json when present.

Rates (USD per 1M tokens) come from workspace.config.json -> usage_metrics.rates,
keyed by model family substring ("opus", "sonnet", "haiku", ...). They are
estimates for comparison, not billing. DEFAULT_RATES follow the public price sheet as
of 2026-09 (cache read = 0.1x input, cache write = 1.25x input); verify against
claude.com/pricing and override in the config when the sheet changes.

Signals the report derives per key (command / item / user / session):
  cache%   share of input tokens read from cache — low = the prefix keeps breaking
  cold/req requests where cache writes exceeded cache reads (model/effort switch,
           expired cache, or a fresh session) — many per command = mid-session flips
  ctx_max  largest single request seen — a curve that only climbs is a session that
           should have been cleared
  $/pass   (--by model) cost per item marked `pass` via --outcome; failed attempts count
"""
import collections
import datetime
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LEDGER = ROOT / "reports" / "usage.jsonl"
DEFAULT_RATES = {"opus": {"in": 5, "out": 25, "cache_read": 0.5, "cache_write": 6.25},
                 "sonnet": {"in": 2, "out": 10, "cache_read": 0.2, "cache_write": 2.5},
                 "haiku": {"in": 1, "out": 5, "cache_read": 0.1, "cache_write": 1.25}}


def current_user():
    import os
    import subprocess
    u = os.environ.get("USAGE_USER")
    if not u:
        try:
            u = subprocess.run(["git", "-C", str(ROOT), "config", "user.email"], capture_output=True,
                               text=True, timeout=5).stdout.strip()
        except Exception:
            u = ""
    try:
        sys.path.insert(0, str(ROOT / "modules" / "_lib"))
        from people import canon
        return canon(u) or "unknown"
    except Exception:
        return u or "unknown"


def rates():
    try:
        cfg = json.loads((ROOT / "workspace.config.json").read_text(encoding="utf-8"))
        return cfg.get("usage_metrics", {}).get("rates") or DEFAULT_RATES
    except Exception:
        return DEFAULT_RATES


def family(model, table):
    m = (model or "").lower()
    return next((k for k in table if k in m), "other")


def is_prompt(e):
    if e.get("type") != "user":
        return False
    c = (e.get("message") or {}).get("content")
    if isinstance(c, str):
        return True
    return isinstance(c, list) and any(b.get("type") == "text" for b in c if isinstance(b, dict))


def text_of(e):
    c = (e.get("message") or {}).get("content")
    if isinstance(c, str):
        return c
    return " ".join(b.get("text", "") for b in c if isinstance(b, dict) and b.get("type") == "text")


def ts(e):
    try:
        return datetime.datetime.fromisoformat(e["timestamp"].replace("Z", "+00:00"))
    except Exception:
        return None


def hook():
    payload = json.load(sys.stdin)
    tp = Path(payload.get("transcript_path", ""))
    if not tp.exists():
        return
    entries = [json.loads(l) for l in tp.read_text(encoding="utf-8").splitlines() if l.strip()]
    starts = [i for i, e in enumerate(entries) if is_prompt(e)]
    if not starts:
        return
    turn = entries[starts[-1]:]
    prompt = text_of(turn[0])
    # sticky command: the most recent slash command in the session
    cmd, args = "chat", ""
    for e in reversed(entries[:starts[-1] + 1]):
        if e.get("type") == "user":
            m = re.search(r"<command-name>/?([\w:-]+)</command-name>", text_of(e))
            if m:
                cmd = m.group(1)
                a = re.search(r"<command-args>(.*?)</command-args>", text_of(e), re.S)
                args = a.group(1).strip() if a else ""
                break
    items = re.findall(r"\b[A-Z]{0,4}-?\d{1,6}\b", args) or ["-"]
    table = rates()
    tok = collections.Counter()
    cost = collections.Counter()
    seen = set()
    requests = cold = ctx_max = 0
    for e in turn:
        msg = e.get("message") or {}
        u = msg.get("usage")
        if e.get("type") != "assistant" or not u or msg.get("id") in seen:
            continue
        seen.add(msg.get("id"))
        fam = family(msg.get("model"), table)
        r = table.get(fam, {})
        parts = {"in": u.get("input_tokens", 0), "out": u.get("output_tokens", 0),
                 "cache_read": u.get("cache_read_input_tokens", 0),
                 "cache_write": u.get("cache_creation_input_tokens", 0)}
        for k, v in parts.items():
            tok[k] += v
            cost[fam] += v * r.get(k, 0) / 1e6
        requests += 1
        cold += parts["cache_write"] > parts["cache_read"]
        ctx_max = max(ctx_max, parts["in"] + parts["cache_read"] + parts["cache_write"])
    t0, t1 = ts(turn[0]), ts(turn[-1])
    rec = {"v": 2, "type": "turn", "date": datetime.date.today().isoformat(),
           "session_id": payload.get("session_id"), "user": current_user(),
           "command": cmd, "items": items, "tokens": dict(tok),
           "requests": requests, "cold_requests": cold, "ctx_max": ctx_max,
           "cost_by_model": {k: round(v, 4) for k, v in cost.items()},
           "cost_usd": round(sum(cost.values()), 4),
           "wall_seconds": round((t1 - t0).total_seconds()) if t0 and t1 else None,
           "prompt_preview": prompt[:80]}
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def ledger_lines():
    if not LEDGER.exists():
        sys.exit("No ledger yet.")
    rows = [json.loads(l) for l in LEDGER.read_text(encoding="utf-8").splitlines() if l.strip()]
    turns = [r for r in rows if r.get("type", "turn") == "turn"]
    outcomes = {r["item"]: r["outcome"] for r in rows if r.get("type") == "outcome"}
    return turns, outcomes


def outcome(item, value):
    if value not in ("pass", "fail", "open"):
        sys.exit("outcome must be pass | fail | open")
    rec = {"v": 2, "type": "outcome", "date": datetime.date.today().isoformat(),
           "user": current_user(), "item": item, "outcome": value}
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"recorded {item}: {value}")


def _acc():
    return {"turns": 0, "cost": 0.0, "in": 0, "read": 0, "write": 0, "req": 0, "cold": 0, "ctx": [], "cmds": []}


def _add(a, r, share=1.0):
    t = r.get("tokens", {})
    a["turns"] += 1
    a["cost"] += r.get("cost_usd", 0) * share
    a["in"] += t.get("in", 0)
    a["read"] += t.get("cache_read", 0)
    a["write"] += t.get("cache_write", 0)
    a["req"] += r.get("requests", 0)
    a["cold"] += r.get("cold_requests", 0)
    if r.get("ctx_max"):
        a["ctx"].append(r["ctx_max"])
    if r.get("command") not in a["cmds"]:
        a["cmds"].append(r.get("command"))


def _cache_pct(a):
    tot = a["in"] + a["read"] + a["write"]
    return f"{100 * a['read'] / tot:5.1f}%" if tot else "    -"


def report(by):
    turns, outcomes = ledger_lines()
    if by == "model":
        agg = collections.defaultdict(lambda: [0, 0.0])
        for r in turns:
            for m, c in r.get("cost_by_model", {}).items():
                agg[(r["command"], m)][0] += 1
                agg[(r["command"], m)][1] += c
        for k, (n, c) in sorted(agg.items(), key=lambda x: -x[1][1]):
            print(f"{str(k):<40} turns={n:<6} est_usd={c:,.2f}")
        per_model_pass(turns, outcomes)
        return
    agg = collections.defaultdict(_acc)
    for r in turns:
        if by == "session":
            _add(agg[(r.get("date"), str(r.get("session_id"))[:8])], r)
            continue
        for it in r["items"]:
            key = r["command"] if by == "command" else (r.get("user", "unknown") if by == "user" else it)
            _add(agg[key], r, 1 / max(1, len(r["items"])))
    print(f"{'key':<44} {'turns':>5} {'est_usd':>8} {'cache%':>6} {'cold/req':>8} {'ctx_max':>9}"
          + ("  outcome" if by == "item" else "  growth" if by == "session" else ""))
    for k, a in sorted(agg.items(), key=lambda x: -x[1]["cost"]):
        ctx = f"{max(a['ctx']):>9,}" if a["ctx"] else f"{'-':>9}"
        cold = f"{a['cold']}/{a['req']}" if a["req"] else "-"
        line = f"{str(k):<44} {a['turns']:>5} {a['cost']:>8,.2f} {_cache_pct(a):>6} {cold:>8} {ctx}"
        if by == "item":
            line += f"  {outcomes.get(k, '')}"
        if by == "session":
            growth = f"{a['ctx'][0]:,} -> {a['ctx'][-1]:,}" if len(a["ctx"]) > 1 else "-"
            line += f"  {growth}  [{', '.join(a['cmds'])}]"
        print(line)
    print("cache% = cache reads / all input; cold/req = requests that rebuilt the cache / requests "
          "(v2 lines only); ctx_max = largest single request")


def per_model_pass(turns, outcomes):
    """Per model: items touched, passed, avg turns, $/turn, $/pass (item model = family with most cost)."""
    items = collections.defaultdict(lambda: {"turns": 0, "cost": 0.0, "models": collections.Counter()})
    for r in turns:
        for it in r["items"]:
            if it == "-":
                continue
            a = items[it]
            a["turns"] += 1
            a["cost"] += r.get("cost_usd", 0) / max(1, len(r["items"]))
            for m, c in r.get("cost_by_model", {}).items():
                a["models"][m] += c
    if not items:
        return
    by_model = collections.defaultdict(list)
    for it, a in items.items():
        dom = a["models"].most_common(1)[0][0] if a["models"] else "other"
        by_model[dom].append((it, a))
    print()
    print(f"{'model':<10} {'items':>5} {'passed':>6} {'avg turns':>9} {'$/turn':>8} {'$/pass':>8}")
    for m, rows in sorted(by_model.items()):
        n = len(rows)
        passed = sum(1 for it, _ in rows if outcomes.get(it) == "pass")
        turns_n = sum(a["turns"] for _, a in rows)
        cost = sum(a["cost"] for _, a in rows)
        per_pass = f"{cost / passed:8.3f}" if passed else f"{'-':>8}"
        print(f"{m:<10} {n:>5} {passed:>6} {turns_n / n:>9.1f} {cost / max(1, turns_n):>8.4f} {per_pass}")
    unmarked = [it for it in items if it not in outcomes]
    if unmarked:
        print(f"no outcome recorded for {len(unmarked)} item(s) — `--outcome <ID> pass|fail|open` after export")


def transcripts_dir():
    base = Path.home() / ".claude" / "projects"
    slug = re.sub(r"[^A-Za-z0-9]", "-", str(ROOT))
    for cand in (base / slug, base / slug.lstrip("-")):
        if cand.exists():
            return cand
    return None


def check():
    """Heartbeat: hook configured? ledger fresh relative to the latest session transcript?"""
    ok = True
    settings = [ROOT / ".claude" / "settings.local.json", ROOT / ".claude" / "settings.json"]
    configured = any("usage_tracker.py" in p.read_text(encoding="utf-8") for p in settings if p.exists())
    print(f"hook configured in .claude/settings*.json : {'yes' if configured else 'NO'}")
    ok &= configured
    last = None
    if LEDGER.exists():
        lines = [l for l in LEDGER.read_text(encoding="utf-8").splitlines() if l.strip()]
        last = LEDGER.stat().st_mtime if lines else None
        print(f"ledger lines                              : {len(lines)}")
    else:
        print("ledger                                    : MISSING (reports/usage.jsonl)")
    td = transcripts_dir()
    if td:
        newest = max((p.stat().st_mtime for p in td.glob("*.jsonl")), default=None)
        if newest:
            lag_h = (newest - (last or 0)) / 3600
            fmt = lambda t: datetime.datetime.fromtimestamp(t).isoformat(timespec="minutes") if t else "never"
            print(f"newest session transcript                 : {fmt(newest)}")
            print(f"last ledger write                         : {fmt(last)}")
            if last is None or lag_h > 1:
                print("STALE: sessions ran after the last ledger write — the hook is not recording "
                      "(restart the agent / open /hooks, check the python command in settings)")
                ok = False
    else:
        print("session transcripts                       : not found under ~/.claude/projects (cannot compare)")
    print("HEARTBEAT: OK" if ok else "HEARTBEAT: FAIL")
    return 0 if ok else 1


def coverage(ledgers, since):
    sys.path.insert(0, str(ROOT / "modules" / "_lib"))
    from people import roster, canon
    seen = collections.Counter()
    for lp in ledgers:
        for l in Path(lp).read_text(encoding="utf-8").splitlines():
            if not l.strip():
                continue
            r = json.loads(l)
            if r.get("type", "turn") != "turn" or (since and r.get("date", "") < since):
                continue
            seen[canon(r.get("user", "unknown"))] += 1
    people = roster()
    if not people:
        print("context/people.json missing — listing users found in the ledgers only")
    missing = [p["name"] for p in people if not seen.get(p["name"])]
    for name, n in sorted(seen.items(), key=lambda x: -x[1]):
        print(f"  {name:<20} {n:>6} turns")
    unknown = [u for u in seen if people and u not in {p['name'] for p in people}]
    if unknown:
        print(f"unmatched users (add as aliases in context/people.json): {', '.join(unknown)}")
    if missing:
        print(f"NO DATA for: {', '.join(missing)} — their hook is not installed or not recording")
    return 1 if missing else 0


if __name__ == "__main__":
    if "--check" in sys.argv:
        sys.exit(check())
    if "--coverage" in sys.argv:
        lds = [str(LEDGER)]
        if "--ledgers" in sys.argv:
            rest = sys.argv[sys.argv.index("--ledgers") + 1:]
            lds = rest[: next((k for k, x in enumerate(rest) if x.startswith("--")), len(rest))]
        since = sys.argv[sys.argv.index("--since") + 1] if "--since" in sys.argv else None
        sys.exit(coverage(lds, since))
    if "--outcome" in sys.argv:
        i = sys.argv.index("--outcome")
        if len(sys.argv) < i + 3:
            sys.exit("usage: --outcome <ID> pass|fail|open")
        outcome(sys.argv[i + 1], sys.argv[i + 2])
    elif "--report" in sys.argv:
        by = sys.argv[sys.argv.index("--by") + 1] if "--by" in sys.argv else "command"
        report(by)
    else:
        try:
            hook()
        except Exception as e:  # a metrics failure must never break the session
            print(f"usage_tracker: {e}", file=sys.stderr)
