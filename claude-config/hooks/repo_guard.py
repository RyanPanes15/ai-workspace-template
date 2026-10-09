"""PreToolUse hook: enforce repo roles from workspace.config.json.

- Edit / Write / MultiEdit / NotebookEdit on a file inside a repo whose policy is
  `read-only` or `flag-only` -> DENY with the reason.
- Bash / PowerShell running a mutating git subcommand (commit, push, merge, rebase,
  reset, checkout -b, switch -c, stash, cherry-pick, revert, tag, am, apply, clean,
  restore) with `git -C <read-only repo>` or after `cd <read-only repo>` -> DENY.
Everything else: no decision.
"""
import json
import os
import re
import sys
from pathlib import Path

from _config import load_config, repo_paths

PROTECTED = {"read-only", "flag-only"}
MUTATING = r'\bgit\b(?:\s+-C\s+("[^"]+"|\'[^\']+\'|\S+))?\s+(commit|push|merge|rebase|reset|checkout\s+-b|switch\s+-c|stash(?!\s+list)|cherry-pick|revert|tag\s+\S|am|apply|clean|restore|rm|mv)\b'


def norm(p):
    return str(p).replace("\\", "/").strip('"\'').rstrip("/").lower()


def real(p):
    return norm(Path(str(p).strip('"\'')).resolve())


def owner(path, repos):
    """The most specific registered repo containing `path` (both resolved), or None."""
    hits = [(name, policy, root) for name, policy, root in repos if path == root or path.startswith(root + "/")]
    return max(hits, key=lambda h: len(h[2]), default=None)


def deny(reason):
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason}}))


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return
    cfg = load_config()
    repos = repo_paths(cfg)
    if not any(policy in PROTECTED for _, policy, _ in repos):
        return
    tool = data.get("tool_name")
    ti = data.get("tool_input") or {}
    if tool in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
        fp = ti.get("file_path") or ti.get("notebook_path") or ""
        hit = owner(real(fp), repos) if fp else None
        if hit and hit[1] in PROTECTED:
            deny(f"Repo '{hit[0]}' is read-only/flag-only per workspace.config.json. "
                 "Surface the needed change instead of editing it.")
    elif tool in ("Bash", "PowerShell"):
        cmd = ti.get("command") or ""
        cwd = norm(data.get("cwd") or "")
        for m in re.finditer(MUTATING, cmd):
            target = norm(m.group(1)) if m.group(1) else None
            cds = re.findall(r'(?:cd|Set-Location|Push-Location)\s+("[^"]+"|\'[^\']+\'|\S+)', cmd[:m.start()])
            where = target or (norm(cds[-1]) if cds else cwd)
            if where and not re.match(r"^([a-z]:)?/", where) and cwd:
                where = norm(os.path.normpath(os.path.join(cwd, where)))
            hit = owner(real(where), repos) if where else None
            if hit and hit[1] in PROTECTED:
                deny(f"Mutating git in read-only repo '{hit[0]}' is not allowed.")
                return


if __name__ == "__main__":
    main()
