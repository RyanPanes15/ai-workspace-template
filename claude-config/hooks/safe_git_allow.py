"""PreToolUse hook: auto-allow only the safe git shapes used by the PR workflow.

Allows without prompting when EVERY statement in the command is one of:
  - an env assignment with a literal value ($env:X = "..." / export X=...)
  - cd / Set-Location / Push-Location
  - git [-C <repo>] pull | fetch            (no force semantics)
  - git [-C <repo>] checkout <branch> | -b <allowed-namespace>/... | <ref> -- <paths>
  - git [-C <repo>] push [-u] origin <allowed-namespace>/...
  - read-only git subcommands (status, log, show, diff, blame, ...)
and at least one statement is a git operation.

Allowed push namespaces come from workspace.config.json -> git.push_namespaces
(default: ["fix", "change", "feature"]). Anything else — other push targets, force
flags, deletes, unrecognized segments, redirections — produces no decision and falls
through to the normal permission prompt. This hook never denies.
"""
import json
import re
import sys

from _config import load_config

GIT = r'^git\s+(?:-C\s+(?:"[^"]+"|\'[^\']+\'|[^\s;|&<>"\']+)\s+)?'


def patterns(namespaces):
    ns = "|".join(re.escape(n.strip("/")) for n in namespaces) or "fix"
    return [
        GIT + rf'push\s+(?:-u\s+)?origin\s+(?:{ns})/[A-Za-z0-9._/-]+$',
        GIT + rf'checkout\s+(?:-b\s+(?:{ns})/[A-Za-z0-9._/-]+|[A-Za-z0-9._/@{{}}-]+(?:\s+--\s+[A-Za-z0-9._/\\ "\'-]+)?)$',
        GIT + r'pull(?:\s+[A-Za-z0-9._/ -]*)?$',
        GIT + r'fetch(?:\s+[A-Za-z0-9._/ -]*)?$',
        GIT + r'(?:status|log|show|diff|blame|shortlog|describe|reflog|rev-parse|rev-list|ls-files|ls-tree|grep|cat-file|stash list)(?:\s+[^;|&<>`$]*)?$',
        GIT + r'branch(?:\s+(?:-a|-r|-vv?|--list|--show-current|--contains)[^;|&<>`$]*)?$',
        GIT + r'remote(?:\s+(?:-v|get-url\s+[^\s;|&<>]+))?$',
    ]


BENIGN = [
    r'^\$env:[A-Za-z_][A-Za-z0-9_]*\s*=\s*(?:"[^"`$]*"|\'[^\']*\')$',
    r'^export\s+[A-Za-z_][A-Za-z0-9_]*=(?:"[^"`$]*"|\'[^\']*\'|[A-Za-z0-9._/\\:%-]+)$',
    r'^(?:cd|Set-Location|Push-Location)\s+(?:"[^"]+"|\'[^\']+\'|[^\s;|&<>"\']+)$',
]


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return
    if data.get("tool_name") not in ("Bash", "PowerShell"):
        return
    cmd = (data.get("tool_input") or {}).get("command") or ""
    if re.search(r'(--force|--force-with-lease|--delete|--mirror|\s-f\b|\s-d\b|\s-D\b)', cmd):
        return
    if re.search(r'[<>`]|\|\|?|\$\(', cmd):
        return
    cfg = load_config()
    git_pats = patterns(cfg.get("git", {}).get("push_namespaces", ["fix", "change", "feature"]))
    stmts = [s.strip() for s in re.split(r'[;\n]|&&', cmd) if s.strip()]
    saw_git = False
    for s in stmts:
        if any(re.match(p, s) for p in git_pats):
            saw_git = True
            continue
        if any(re.match(p, s) for p in BENIGN):
            continue
        return
    if saw_git:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "permissionDecisionReason": "safe git shape (PR workflow allowlist)"}}))


if __name__ == "__main__":
    main()
