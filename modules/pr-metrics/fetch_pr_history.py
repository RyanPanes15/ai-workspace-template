#!/usr/bin/env python3
"""PR delivery history for the workspace's GitHub repos (via the `gh` CLI — no token
handling here; `gh auth login` once).

  python modules/pr-metrics/fetch_pr_history.py                  # all editable/pr-only GitHub repos
  python modules/pr-metrics/fetch_pr_history.py --since 2026-06-01 --repo web
  python modules/pr-metrics/fetch_pr_history.py --summary        # summary from the cache only (no network)

Writes _work/pr-history.json (one entry per PR, cached; merged/closed PRs are not
re-fetched) and prints a summary per repo and per person:
opened · merged · median hours open→merge · +/- lines · files · share of PRs with an
AI co-author trailer.

AI attribution: a PR counts as AI-co-authored when any commit carries a
`Co-Authored-By:` trailer matching `pr_metrics.ai_trailer_pattern` in
workspace.config.json (default: `Claude|noreply@anthropic\\.com`). People are
canonicalised through context/people.json (email / login aliases).
Pair with modules/usage-metrics for cost per merged PR.
"""
import argparse
import datetime
import json
import re
import statistics
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "_work" / "pr-history.json"
sys.path.insert(0, str(ROOT / "modules" / "_lib"))
try:
    from people import canon
except Exception:  # pragma: no cover
    canon = lambda v, path=None: v  # noqa: E731
TRAILER = re.compile(r"^Co-Authored-By:\s*(.+?)\s*$", re.I | re.M)


def gh_json(path):
    r = subprocess.run(["gh", "api", "--paginate", path], capture_output=True, text=True, encoding="utf-8")
    if r.returncode:
        raise RuntimeError(r.stderr.strip()[:300])
    # --paginate emits one JSON document per page back to back; decode them in sequence
    dec, txt, i, out = json.JSONDecoder(), r.stdout, 0, []
    while True:
        while i < len(txt) and txt[i].isspace():
            i += 1
        if i >= len(txt):
            break
        val, i = dec.raw_decode(txt, i)
        if isinstance(val, list):
            out.extend(val)
        else:
            return val
    return out


def gh_repo(remote):
    m = re.search(r"github\.com[:/]([^/]+)/([^/.]+)", remote or "")
    return f"{m.group(1)}/{m.group(2)}" if m else None


def cfg():
    p = ROOT / "workspace.config.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def fetch(repos, since, limit):
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    pat = re.compile(cfg().get("pr_metrics", {}).get("ai_trailer_pattern", r"Claude|noreply@anthropic\.com"), re.I)
    for name, slug in repos:
        prs = gh_json(f"repos/{slug}/pulls?state=all&per_page=100&sort=created&direction=desc")
        n = 0
        for pr in prs:
            if since and pr["created_at"][:10] < since:
                continue
            key = f"{slug}#{pr['number']}"
            if key in cache and cache[key]["state"] in ("merged", "closed"):
                continue
            if limit and n >= limit:
                break
            n += 1
            d = gh_json(f"repos/{slug}/pulls/{pr['number']}")
            commits = gh_json(f"repos/{slug}/pulls/{pr['number']}/commits?per_page=100")
            trailers = sorted({t for c in commits for t in TRAILER.findall(c["commit"]["message"])})
            authors = sorted({(c["commit"]["author"] or {}).get("email", "") for c in commits} - {""})
            cache[key] = {
                "repo": name, "slug": slug, "number": pr["number"], "title": pr["title"],
                "state": "merged" if d.get("merged_at") else pr["state"],
                "author": canon(pr["user"]["login"]), "commit_authors": [canon(a) for a in authors],
                "base": pr["base"]["ref"], "head": pr["head"]["ref"],
                "opened_at": pr["created_at"], "merged_at": d.get("merged_at"), "closed_at": pr.get("closed_at"),
                "additions": d.get("additions", 0), "deletions": d.get("deletions", 0),
                "files_changed": d.get("changed_files", 0), "commits": len(commits),
                "co_authors": trailers, "ai_coauthored": any(pat.search(t) for t in trailers)}
        print(f"  {name:<16} {slug:<40} {n} PR(s) fetched/updated")
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
    return cache


def hours(a, b):
    f = lambda s: datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
    return (f(b) - f(a)).total_seconds() / 3600


def summary(cache, since):
    rows = [p for p in cache.values() if not since or p["opened_at"][:10] >= since]
    if not rows:
        print("no PRs in cache for the window")
        return

    def block(title, groups):
        print(f"\n{title}")
        print(f"  {'':<18} {'opened':>6} {'merged':>6} {'med h→merge':>11} {'+lines':>8} {'-lines':>8} {'AI co-auth':>10}")
        for k, ps in sorted(groups.items()):
            merged = [p for p in ps if p["merged_at"]]
            med = statistics.median([hours(p["opened_at"], p["merged_at"]) for p in merged]) if merged else 0
            ai = sum(p["ai_coauthored"] for p in ps) / len(ps) * 100
            print(f"  {k:<18} {len(ps):>6} {len(merged):>6} {med:>11.1f} {sum(p['additions'] for p in ps):>8} "
                  f"{sum(p['deletions'] for p in ps):>8} {ai:>9.0f}%")

    by_repo, by_person = {}, {}
    for p in rows:
        by_repo.setdefault(p["repo"], []).append(p)
        by_person.setdefault(p["author"], []).append(p)
    block("By repo", by_repo)
    block("By author", by_person)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--since")
    ap.add_argument("--repo")
    ap.add_argument("--limit", type=int, default=0, help="max PRs fetched per repo this run")
    ap.add_argument("--summary", action="store_true", help="no network; summarise the cache")
    a = ap.parse_args()
    if a.summary:
        return summary(json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}, a.since)
    repos = [(r["name"], gh_repo(r.get("remote"))) for r in cfg().get("repos", [])
             if r.get("policy") in ("editable", "pr-only") and gh_repo(r.get("remote"))
             and (not a.repo or r["name"] == a.repo)]
    if not repos:
        sys.exit("no GitHub remotes among editable/pr-only repos in workspace.config.json")
    summary(fetch(repos, a.since, a.limit), a.since)


if __name__ == "__main__":
    main()
