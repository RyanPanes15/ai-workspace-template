#!/usr/bin/env python3
"""Diff-based lint gate for a feature branch that refuses vacuous runs.

Fails when the feature branch is the integration branch, origin/<base> is missing,
the diff has no lintable files, the report is not rewritten, or zero files were linted.

Config — workspace.config.json, per repo (defaults shown are used when absent):
  "lint": {
    "ext": [".ts", ".tsx", ".js", ".jsx"],
    "command": ["npx", "eslint", "{files}", "-f", "checkstyle", "-o", "lint-result-diff.xml"],
    "fix_command": ["npx", "eslint", "--fix", "{files}"],
    "report": "lint-result-diff.xml",          # checkstyle XML, optional
    "report_format": "checkstyle"               # or "exit-code" (pass = exit 0)
  }

Usage:
  python modules/lint-gate/lint_gate.py <repo-name> [feature-branch]      # gate
  python modules/lint-gate/lint_gate.py <repo-name> --working-tree --fix  # Stage-1 auto-fix
  python modules/lint-gate/lint_gate.py <repo-name> --base release/2.3

Exit: 0 pass · 1 lint errors · 2 usage/environment · 3 nothing was linted.
"""
import argparse
import json
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT = {"ext": [".ts", ".tsx", ".js", ".jsx"],
           "command": ["npx", "eslint", "{files}", "-f", "checkstyle", "-o", "lint-result-diff.xml"],
           "fix_command": ["npx", "eslint", "--fix", "{files}"],
           "report": "lint-result-diff.xml", "report_format": "checkstyle"}


def fail(code, msg):
    print(f"LINT GATE: FAIL — {msg}")
    sys.exit(code)


def git(repo, *args, check=True):
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if check and r.returncode != 0:
        raise RuntimeError(r.stderr.strip())
    return r.stdout.strip()


def expand(cmd, files):
    out = []
    for c in cmd:
        out += files if c == "{files}" else [c]
    exe = shutil.which(out[0]) or shutil.which(out[0] + ".cmd")
    if not exe:
        fail(2, f"'{out[0]}' not found on PATH")
    return [exe, *out[1:]]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("repo")
    ap.add_argument("feature", nargs="?")
    ap.add_argument("--base")
    ap.add_argument("--fix", action="store_true")
    ap.add_argument("--working-tree", action="store_true")
    a = ap.parse_args()

    cfg = json.loads((ROOT / "workspace.config.json").read_text(encoding="utf-8")) if (ROOT / "workspace.config.json").exists() else {}
    r = next((x for x in cfg.get("repos", []) if x.get("name") == a.repo), None)
    if not r:
        fail(2, f"repo '{a.repo}' not in workspace.config.json")
    if r.get("policy") in ("read-only", "flag-only"):
        fail(2, f"repo '{a.repo}' is {r['policy']} — nothing to lint")
    repo = Path(r["path"]) if Path(r["path"]).is_absolute() else ROOT / r["path"]
    lint = {**DEFAULT, **r.get("lint", {})}
    base = a.base or r.get("integration_branch") or "develop"
    feature = a.feature or git(repo, "branch", "--show-current")
    if not feature:
        fail(2, "detached HEAD — pass the feature branch")
    if feature in (base, f"origin/{base}"):
        fail(2, f"'{feature}' is the integration branch — pass the FEATURE branch")
    if not git(repo, "rev-parse", "--verify", "--quiet", f"origin/{base}", check=False):
        fail(2, f"origin/{base} not found — git fetch first")
    names = set(git(repo, "diff", "--name-only", f"origin/{base}...{feature}").splitlines())
    if a.working_tree:
        names |= set(git(repo, "diff", "--name-only", "HEAD").splitlines())
        names |= set(git(repo, "ls-files", "--others", "--exclude-standard").splitlines())
    files = sorted(f for f in names if f.endswith(tuple(lint["ext"])) and (repo / f).exists())
    print(f"repo={a.repo} base=origin/{base} feature={feature} changed={len(names)} lintable={len(files)}")
    if not files:
        fail(3, "no lintable files in the diff — nothing was checked")

    if a.fix:
        p = subprocess.run(expand(lint["fix_command"], files), cwd=repo, text=True, capture_output=True, encoding="utf-8", errors="replace")
        print((p.stdout or p.stderr)[-3000:] or "(no output)")
        print("modified by fix:", git(repo, "diff", "--name-only", "--", *files) or "none")
        sys.exit(0 if p.returncode in (0, 1) else 2)

    rep = repo / lint["report"] if lint.get("report") else None
    before = rep.stat().st_mtime if rep and rep.exists() else None
    p = subprocess.run(expand(lint["command"], files), cwd=repo, text=True, capture_output=True, encoding="utf-8", errors="replace")
    if lint["report_format"] == "exit-code":
        print((p.stdout or p.stderr)[-3000:])
        if p.returncode:
            fail(1, f"linter exited {p.returncode}")
        print("LINT GATE: PASS")
        return
    if not rep or not rep.exists() or (before is not None and rep.stat().st_mtime <= before):
        fail(2, f"report not (re)written (exit {p.returncode}): {(p.stderr or p.stdout)[-1200:]}")
    errors, warnings, linted = [], 0, 0
    for f in ET.parse(rep).getroot().iter("file"):
        linted += 1
        for e in f.iter("error"):
            if e.get("severity") == "error":
                errors.append(f"  {f.get('name')}:{e.get('line')}  {e.get('message')}  [{e.get('source')}]")
            else:
                warnings += 1
    if linted == 0:
        fail(3, "report lists zero files — the linter checked nothing")
    print(f"checked {linted} file(s): {len(errors)} error(s), {warnings} warning(s)")
    print("\n".join(errors[:50]))
    if errors:
        fail(1, "fix, commit as a NEW lint-fix commit (no --amend), re-run")
    print("LINT GATE: PASS")


if __name__ == "__main__":
    main()
