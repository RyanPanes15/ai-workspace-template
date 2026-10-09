#!/usr/bin/env python3
"""Bootstrap this agent workspace for a new project.

Registers the project's repos (frontend, backend, and any additional context repos:
database/schema, reports, docs, tests, legacy/reference, infra, other), clones or
links them, detects their stacks, and generates:

  workspace.config.json            single source of truth (re-run safe)
  AGENTS.md  (WORKSPACE-MAP block) repo map, ownership routing, git naming
  context/repos/<name>.md          per-repo context stub (never overwritten)
  .claude/rules/repo-<name>.md     path-scoped per-repo rule (regenerated every render)
  .claude/                         installed from claude-config/ on first run
  .claude/settings.local.json      optional hooks (usage metrics)
  secrets/                         gitignored credentials folder

Usage:
  python setup/setup_workspace.py                  interactive
  python setup/setup_workspace.py --config a.json  non-interactive (answers file)
  python setup/setup_workspace.py --render         re-render from workspace.config.json
  python setup/setup_workspace.py --check          validate repos/paths/branches
  python setup/setup_workspace.py --install-global copy docs/global-defaults.md block
                                                   to ~/.claude/CLAUDE.md (with backup)
  add --dry-run to print what would change without writing.

Nothing inside the project repos is modified. Cloning happens only after you confirm.
"""
import argparse
import datetime
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "workspace.config.json"
AGENTS = ROOT / "AGENTS.md"
CTX = ROOT / "context" / "repos"
BEGIN = "<!-- BEGIN:WORKSPACE-MAP"
END = "<!-- END:WORKSPACE-MAP -->"
PBEGIN = "<!-- BEGIN:PROFILE"
PEND = "<!-- END:PROFILE -->"
PROFILES_DIR = ROOT / "profiles"
TYPE_ORDER = ["greenfield", "maintenance", "port", "feature"]
DRY = False

# role -> (label, default policy, why it helps, what happens without it)
ROLES = {
    "frontend": ("Frontend / client", "editable",
                 "UI screens, forms, client state — where most UI defects are fixed",
                 "UI items can only be analyzed from reports and API behavior"),
    "backend": ("Backend / API", "editable",
                "endpoints, validation schemas, business logic, SQL",
                "cross-layer verification (client value vs API schema) cannot run"),
    "database": ("Database / schema-as-code", "read-only",
                 "DDL, constraints, views, migrations — column widths and nullability",
                 "DB constraints come only from a live DB (modules/db-query) or a schema snapshot"),
    "reports": ("Reports / document generation", "flag-only",
                "report templates, PDF/XLS generation",
                "report-output defects can only be traced to the data the API sends"),
    "docs": ("Docs / specs / knowledge base", "pr-only",
             "authoritative specs, ER notes, curated AI knowledge — first-touch reference",
             "domain questions fall back to reverse-engineering code (slower, less accurate)"),
    "tests": ("Tests / QA automation", "read-only",
              "E2E suites, QA knowledge, test data, tester tooling",
              "verification uses only the app repos' own test harnesses"),
    "legacy-frontend": ("Legacy / reference client", "read-only",
                        "the system being replaced — the de-facto spec in defect mode",
                        "port-regression analysis (Tier 2) is unavailable for UI behavior"),
    "legacy-backend": ("Legacy / reference server", "read-only",
                       "reference server logic and SQL",
                       "port-regression analysis (Tier 2) is unavailable for server behavior"),
    "legacy-database": ("Legacy / reference schema", "read-only",
                        "reference DDL and stored procedures", "reference data rules are unavailable"),
    "infra": ("Infra / deploy / CI", "read-only",
              "pipelines, environment config, deploy scripts", "environment defects need manual context"),
    "other": ("Other context repo", "read-only", "anything else agents should be able to read", ""),
}
PRIMARY = ["frontend", "backend"]
ADDITIONAL = [r for r in ROLES if r not in PRIMARY]
POLICIES = ["editable", "pr-only", "flag-only", "read-only"]
POLICY_TEXT = {
    "editable": "Yes — fixes land here via topic branch + PR",
    "pr-only": "Only via a developer-initiated PR (ask first)",
    "flag-only": "No — investigate, then surface the needed change",
    "read-only": "No — reference only; never edit, never run mutating git",
}


# ───────────────────────── helpers ─────────────────────────

def say(msg=""):
    print(msg)


def ask(q, default=None, choices=None, required=False):
    hint = f" [{default}]" if default not in (None, "") else ""
    if choices:
        hint = f" ({'/'.join(choices)})" + hint
    while True:
        try:
            v = input(f"  {q}{hint}: ").strip()
        except EOFError:
            v = ""
        if not v and default is not None:
            v = default
        if choices and v and v not in choices:
            say(f"    choose one of: {', '.join(choices)}")
            continue
        if required and not v:
            continue
        return v


def yes(q, default=True):
    return ask(q + " (y/n)", "y" if default else "n").lower().startswith("y")


def run(cmd, cwd=None):
    try:
        return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=60).stdout.strip()
    except Exception:
        return ""


def write(path, text):
    path = Path(path)
    shown = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
    if DRY:
        say(f"  [dry-run] would write {shown} ({len(text)} bytes)")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    say(f"  wrote {shown}")


def slug(s):
    return re.sub(r"[^a-z0-9-]+", "-", s.lower()).strip("-") or "repo"


def python_cmd():
    if platform.system() == "Windows" and not shutil.which("python") and shutil.which("py"):
        return "py"
    return "python" if shutil.which("python") else "python3"


# ───────────────────────── detection ─────────────────────────

def resolve(p):
    p = Path(os.path.expanduser(p))
    return p if p.is_absolute() else (ROOT / p)


def detect_git(path):
    if not (path / ".git").exists():
        return {}
    head = run(["git", "symbolic-ref", "--short", "refs/remotes/origin/HEAD"], cwd=path)
    return {"remote": run(["git", "remote", "get-url", "origin"], cwd=path),
            "default_branch": head.split("/", 1)[1] if "/" in head else run(["git", "branch", "--show-current"], cwd=path)}


QUIET_BY_FILE = {
    "pyproject.toml": ["`pytest -q -x --no-header -p no:cacheprovider <file>` — one file, stop at first failure",
                       "`ruff check --output-format=concise .` — lint, one line per finding"],
    "requirements.txt": ["`pytest -q -x --no-header <file>` — one file, stop at first failure"],
    "go.mod": ["`go test ./... 2>&1 | grep -v '^ok'` — failures only", "`go vet ./...`"],
    "Cargo.toml": ["`cargo test -q 2>&1 | grep -v 'ok$'` — failures only"],
    "pom.xml": ["`mvn -q -Dsurefire.printSummary=false test` — quiet; failures still print"],
    "build.gradle": ["`gradle test -q` — quiet; failures still print"],
    "build.gradle.kts": ["`gradle test -q` — quiet; failures still print"],
}


def quiet_node(deps):
    """Failures-only invocations for the detected Node tooling (flags to confirm per repo)."""
    q = []
    if "vitest" in deps:
        q.append("`npx vitest run <file> --reporter=dot` — one file, dots only")
    if "jest" in deps:
        q.append("`npx jest <file> --silent --reporters=summary` — one file, summary only")
    if "mocha" in deps:
        q.append("`npx mocha <file> --reporter dot`")
    if "@playwright/test" in deps or "playwright" in deps:
        q.append("`npx playwright test <file> --reporter=dot`")
    if "eslint" in deps:
        q.append("`npx eslint <files> --quiet -f unix` — errors only, one line each")
    if "typescript" in deps:
        q.append("`npx tsc --noEmit --pretty false` — errors only, one line each")
    return q


def detect_stack(path):
    stack, cmds, quiet = [], [], []
    pj = path / "package.json"
    if pj.exists():
        try:
            d = json.loads(pj.read_text(encoding="utf-8"))
            deps = {**d.get("dependencies", {}), **d.get("devDependencies", {})}
            known = ["react", "next", "vue", "nuxt", "@angular/core", "svelte", "vite", "webpack", "express",
                     "@nestjs/core", "fastify", "koa", "typescript", "zustand", "redux", "@reduxjs/toolkit",
                     "formik", "react-hook-form", "zod", "joi", "yup", "@mui/material", "tailwindcss",
                     "jest", "vitest", "mocha", "puppeteer", "playwright", "@playwright/test", "cypress",
                     "prisma", "typeorm", "sequelize", "knex", "oracledb", "pg", "mysql2", "eslint", "prettier"]
            stack.append("Node: " + ", ".join(f"{k} {deps[k]}" for k in known if k in deps) or "Node")
            for s in ("dev", "start", "build", "test", "lint", "lint:fix", "format", "test:integration", "typecheck"):
                if s in d.get("scripts", {}):
                    cmds.append(f"`npm run {s}` → `{d['scripts'][s]}`")
            quiet += quiet_node(deps)
        except Exception:
            stack.append("Node (package.json unreadable)")
    for f, label in [("pom.xml", "Java/Maven"), ("build.gradle", "Java/Gradle"), ("build.gradle.kts", "Kotlin/Gradle"),
                     ("pyproject.toml", "Python (pyproject)"), ("requirements.txt", "Python (requirements)"),
                     ("go.mod", "Go"), ("Cargo.toml", "Rust"), ("composer.json", "PHP/Composer"),
                     ("Gemfile", "Ruby"), ("pubspec.yaml", "Dart/Flutter")]:
        if (path / f).exists():
            stack.append(label)
            quiet += QUIET_BY_FILE.get(f, [])
    if list(path.glob("*.sln")) or list(path.glob("*.csproj")) or list(path.glob("src/**/*.csproj"))[:1]:
        stack.append(".NET / C#")
        quiet.append("`dotnet test --nologo -v q --filter <Name>` — quiet; failures still print")
    sql = list(path.glob("**/*.sql"))[:1] or list(path.glob("**/*.ddl"))[:1]
    if sql:
        stack.append("SQL files present")
    for f in ("lint_check.sh", "Makefile", "docker-compose.yml", ".husky"):
        if (path / f).exists():
            cmds.append(f"`{f}` present")
    own = [f for f in ("AGENTS.md", "CLAUDE.md", ".cursorrules", ".github/copilot-instructions.md") if (path / f).exists()]
    return stack, cmds, own, quiet


# ───────────────────────── project profiles ─────────────────────────

def load_profile(t):
    f = PROFILES_DIR / t / "profile.json"
    if not f.exists():
        sys.exit(f"unknown project type '{t}' (choose from: {', '.join(TYPE_ORDER)})")
    return json.loads(f.read_text(encoding="utf-8"))


def normalize(cfg):
    """Rewrite the old single `project` block as `projects: [...]` owning every repo."""
    p = cfg.pop("project", None)
    if p is None or "projects" in cfg:
        return cfg
    out = {k: p.pop(k) for k in ("source_language", "stakeholder_language") if k in p}
    p["repos"] = [r["name"] for r in cfg.get("repos", [])]
    out["projects"] = [p]
    out.update(cfg)
    return out


def project_profiles(p):
    return [load_profile(t) for t in p.get("types", [])]


def active_profiles(cfg):
    """Distinct profiles across all projects, in type order."""
    types = {t for p in cfg.get("projects", []) for t in p.get("types", [])}
    return [load_profile(t) for t in TYPE_ORDER if t in types]


def ctx_dir(p):
    return f"context/projects/{p['name']}"


def find_project(cfg, name):
    names = [p["name"] for p in cfg.get("projects", [])]
    if name not in names:
        sys.exit(f"unknown project '{name}' (projects: {', '.join(names) or 'none'})")
    return cfg["projects"][names.index(name)]


def repo_projects(cfg, name):
    """(projects the repo belongs to, projects that use it as a reference)."""
    ps = cfg.get("projects", [])
    return ([p["name"] for p in ps if name in p.get("repos", [])],
            [p["name"] for p in ps if name in p.get("reference_repos", [])])


def project_roles(cfg, p):
    roles = {r["role"] for r in cfg.get("repos", []) if r["name"] in p.get("repos", [])}
    if p.get("reference_repos"):
        roles |= {"legacy-frontend", "legacy-backend", "legacy-database"}
    return roles


def validate_projects(cfg):
    names = {r["name"] for r in cfg.get("repos", [])}
    for p in cfg.get("projects", []):
        unknown = [n for n in p.get("repos", []) + p.get("reference_repos", []) if n not in names]
        if unknown:
            sys.exit(f"project '{p['name']}' lists unknown repo(s): {', '.join(unknown)}")


def parse_types(text):
    alias = {"1": "greenfield", "new": "greenfield", "fresh": "greenfield", "2": "maintenance", "bugfix": "maintenance",
             "bug-fix": "maintenance", "3": "port", "migration": "port", "4": "feature", "features": "feature"}
    out = []
    for t in re.split(r"[,\s]+", text.strip().lower()):
        t = alias.get(t, t)
        if t and t not in out:
            load_profile(t)
            out.append(t)
    return out


def apply_type_defaults(cfg, explicit=()):
    """Set each project's modes from its profiles and switch on their default modules (never off)."""
    for p in cfg.get("projects", []):
        if p.get("types"):
            p["modes"] = list(dict.fromkeys(pr["mode"] for pr in project_profiles(p)))
    m = cfg.setdefault("modules", {})
    for pr in active_profiles(cfg):
        for k, v in pr.get("modules", {}).items():
            if k not in explicit:
                m[k] = bool(m.get(k)) or v


def skipped_roles(profs):
    skip = set()
    for pr in profs:
        skip |= set(pr.get("skip_roles", []))
    for pr in profs:  # a role another active type needs is never skipped
        skip -= set(pr.get("recommended_roles", []))
        for grp in pr.get("required_roles", []):
            skip -= set(grp if isinstance(grp, list) else [grp])
    return skip


def missing_required(cfg):
    out = []
    for p in cfg.get("projects", []):
        roles = project_roles(cfg, p)
        for pr in project_profiles(p):
            for grp in pr.get("required_roles", []):
                grp = grp if isinstance(grp, list) else [grp]
                if not roles & set(grp):
                    out.append((p["name"], pr["label"], " or ".join(ROLES[g][0] for g in grp)))
    return out


def render_profile(cfg):
    projects = [p for p in cfg.get("projects", []) if p.get("types")]
    head = f"{PBEGIN} (generated from profiles/ by setup — change with --set-type --project) -->"
    if not projects:
        return "\n".join([head, "### Active project profiles", "",
                          "_No project type set. Run `python setup/setup_workspace.py --set-type <greenfield|maintenance|port|feature>"
                          " --project <name>` (see docs/project-types.md)._", PEND])
    L = [head, "### Active project profiles", "",
         "A work item follows the profile of the project that owns the repo it is in (§1 Projects, and the "
         "repo's `.claude/rules` file). `<project>` in a path means that project's name.", ""]
    for p in projects:
        L.append(f"- `{p['name']}`: " + " + ".join(pr["label"] for pr in project_profiles(p))
                 + f" · modes {', '.join(p.get('modes', []))} · context `{ctx_dir(p)}/`")
    if any(len(p["types"]) > 1 for p in projects):
        L += ["", "A project with several types runs each work item under the mode of the workflow that handles it "
              "(build / defect / port / change); when unsure which applies, ask."]
    L.append("")
    for pr in active_profiles(cfg):
        users = [p["name"] for p in projects if pr["type"] in p["types"]]
        text = (PROFILES_DIR / pr["type"] / "AGENTS.profile.md").read_text(encoding="utf-8").strip()
        first, _, rest = text.partition("\n")
        L += [first, "", "Applies to: " + ", ".join(f"`{u}`" for u in users) + ".", rest.rstrip()]
        L += ["", "**Source of truth, in order:** " + " → ".join(pr["truth_order"]) + ".",
              "**Primary commands:** " + ", ".join(f"`{c}`" for c in pr["primary_commands"]) + ".",
              "**Always open from `mistakes/`:** " + ", ".join(f"`{m}`" for m in pr.get("always_read_mistakes", [])) + ".", ""]
    L.append(PEND)
    return "\n".join(L)


def apply_profile(cfg):
    text = AGENTS.read_text(encoding="utf-8")
    block = render_profile(cfg)
    if PBEGIN in text and PEND in text:
        text = text[:text.index(PBEGIN)] + block + text[text.index(PEND) + len(PEND):]
    else:
        text = text.replace("\n---\n\n## 3.", "\n" + block + "\n\n---\n\n## 3.", 1)
    write(AGENTS, text)
    for p in cfg.get("projects", []):
        for pr in project_profiles(p):
            for rel in pr.get("scaffold", []):
                src = PROFILES_DIR / rel
                sub = Path(*Path(rel).parts[2:])  # drop "<type>/scaffold/"
                dst = ROOT / ctx_dir(p) / Path(*sub.parts[1:]) if sub.parts[0] == "context" else ROOT / sub
                if dst.exists():
                    continue
                write(dst, src.read_text(encoding="utf-8"))


# ───────────────────────── interactive ─────────────────────────

def banner():
    say("=" * 72)
    say(" Agent workspace setup")
    say("=" * 72)
    say(" I'll register the project's repos so agents know where code lives, who")
    say(" owns what, and what they may change. You'll be asked for:")
    say("")
    say("   1. Frontend repo      — " + ROLES["frontend"][2])
    say("   2. Backend repo       — " + ROLES["backend"][2])
    say("   3. Additional repos that give agents extra context:")
    for r in ADDITIONAL:
        say(f"        · {ROLES[r][0]:<32} {ROLES[r][2]}")
    say("")
    say(" Each repo can be a git URL (cloned into repos/) or an existing local path")
    say(" (linked, not copied). Press Enter to skip any role.")
    say("")


def ask_repo(role, existing_names, note="", allow_create=False):
    label, pol, why, _ = ROLES[role]
    say(f"\n── {label} ──  ({why}){note}")
    src = ask("git URL or local path (Enter to skip)" + (", or a new path to create" if allow_create else ""), "")
    if not src:
        return None
    is_url = bool(re.match(r"^(https?://|git@|ssh://)", src))
    guess = slug(Path(src.rstrip("/").split("/")[-1].replace(".git", "")).name)
    name = ask("short name", guess)
    while name in existing_names:
        name = ask("name taken — another short name", name + "-2")
    repo = {"name": name, "role": role}
    if is_url:
        repo["remote"] = src
        repo["path"] = f"repos/{name}"
    else:
        repo["path"] = src
    repo["policy"] = ask("policy", pol, POLICIES)
    path = resolve(repo["path"])
    if not is_url and not path.exists() and allow_create and yes(f"{repo['path']} does not exist — create it and git init?", True):
        repo["create"] = True
    g = detect_git(path) if path.exists() else {}
    if repo["policy"] in ("editable", "pr-only"):
        repo["integration_branch"] = ask("integration branch PRs target", g.get("default_branch") or "develop")
        repo["protected_branches"] = [b.strip() for b in ask(
            "protected branches (comma-separated)", f"main,master,{repo['integration_branch']}").split(",") if b.strip()]
    if role.startswith("legacy"):
        repo["reference"] = True
    notes = ask("one-line note (what lives here, owner team) — optional", "")
    if notes:
        repo["notes"] = notes
    return repo


def interactive(cfg):
    banner()
    cfg = normalize(cfg)
    projects = cfg.setdefault("projects", [])
    say("── Project ──")
    if projects:
        say("  existing projects: " + ", ".join(p["name"] for p in projects) + " (enter one to update it, or a new name)")
    name = ask("project name", projects[0]["name"] if len(projects) == 1 else ROOT.name, required=True)
    p = next((q for q in projects if q["name"] == name), None)
    if p is None:
        p = {"name": name}
        projects.append(p)
    p["description"] = ask("one-line description", p.get("description", ""))
    cfg["stakeholder_language"] = ask("language for stakeholder replies", cfg.get("stakeholder_language", "English"))
    cfg["source_language"] = ask("language of tickets/reports (for translation)", cfg.get("source_language", "English"))
    say("\n  Project type (comma-separate if more than one — see docs/project-types.md):")
    for i, t in enumerate(TYPE_ORDER, 1):
        say(f"    {i}. {t:<12} {load_profile(t)['label']}")
    p["types"] = parse_types(ask("type(s)", ",".join(p.get("types", [])) or "maintenance", required=True))
    apply_type_defaults(cfg)
    profs = project_profiles(p)
    allow_create = any(pr.get("allow_create_repos") for pr in profs)
    required = {g for pr in profs for grp in pr.get("required_roles", []) for g in (grp if isinstance(grp, list) else [grp])}
    recommended = {g for pr in profs for g in pr.get("recommended_roles", [])}
    skip = skipped_roles(profs)

    used = {n for q in projects if q is not p for n in q.get("repos", []) + q.get("reference_repos", [])}
    kept = [r for r in cfg.get("repos", []) if r["name"] not in p.get("repos", []) or r["name"] in used]
    repos = []
    names = {r["name"] for r in kept}
    tag = lambda role: "  [required for this project type]" if role in required else ("  [recommended]" if role in recommended else "")
    for role in PRIMARY:
        r = ask_repo(role, names, tag(role), allow_create)
        if r:
            repos.append(r)
            names.add(r["name"])
    say("\n── Additional context repos ──")
    for role in ADDITIONAL:
        if role in skip:
            continue
        if role == "other":
            while yes("add another context repo?", False):
                r = ask_repo("other", names)
                if r:
                    repos.append(r)
                    names.add(r["name"])
            continue
        if yes(f"do you have a {ROLES[role][0]} repo?{tag(role)}", role in required):
            r = ask_repo(role, names, tag(role), allow_create)
            if r:
                repos.append(r)
                names.add(r["name"])
    cfg["repos"] = kept + repos
    p["repos"] = [r["name"] for r in repos]

    g = cfg.setdefault("git", {})
    say("\n── Git conventions ──")
    g["fix_branch"] = ask("fix branch pattern", g.get("fix_branch", "fix/{area}/{item}"))
    g["change_branch"] = ask("change-request branch pattern", g.get("change_branch", "change/{area}/{item}"))
    g["commit"] = ask("commit header pattern", g.get("commit", "{area}: ({item}) {summary}"))
    g["pr_title"] = ask("PR title pattern", g.get("pr_title", "[{ITEM}] {summary}"))
    g["push_namespaces"] = sorted({b.split("/")[0] for b in (g["fix_branch"], g["change_branch"])} | {"feature"})

    m = cfg.setdefault("modules", {})
    say("\n── Optional modules ──")
    m["tracker"] = yes("tracker fetcher (CSV / JSON / Google Sheet / GitHub Issues → _work/items)?", m.get("tracker", True))
    m["db_query"] = yes("read-only DB query wrapper?", m.get("db_query", False))
    m["usage_metrics"] = yes("per-turn usage/cost ledger (Stop hook)?", m.get("usage_metrics", False))
    m["log_triage"] = yes("log triage (fingerprint + whitelist + symbolicate, /log-triage)?", m.get("log_triage", False))
    m["pr_metrics"] = yes("PR delivery metrics via gh (pr-metrics)?", m.get("pr_metrics", False))
    m["parity"] = yes("is there a sibling workspace (tester/admin) sharing files with this one?", m.get("parity", False))
    if m["parity"]:
        sib = cfg.setdefault("parity_workspaces", [])
        while True:
            path = ask("sibling workspace path (Enter to finish)", "")
            if not path:
                break
            sib.append({"name": slug(ask("short name", Path(path).name)), "root": path})
    if m["tracker"] and not cfg.get("tracker", {}).get("sources"):
        cfg["tracker"] = {"sources": [], "enums": {}, "translate_fields": []}
        while yes("add a tracker source now?", True):
            s = {"name": slug(ask("source name", "items")),
                 "type": ask("type", "csv", ["csv", "json", "gsheet", "github"]),
                 "location": ask("location (path / sheet id / owner/repo)", required=True),
                 "id_prefix": ask("ID prefix for this source (Enter for bare numbers)", ""),
                 "id_field": ask("ID column/field", "id")}
            cfg["tracker"]["sources"].append(s)
    return cfg


# ───────────────────────── materialize ─────────────────────────

def clone_missing(cfg, assume_yes=False):
    for r in cfg["repos"]:
        path = resolve(r["path"])
        if not path.exists() and r.get("create") and not r.get("remote"):
            if r["role"].startswith("legacy"):
                say(f"  skipped creating {r['path']}: a reference repo must already exist — give its URL or path")
                continue
            if DRY:
                say(f"  [dry-run] mkdir + git init {r['path']}")
                continue
            path.mkdir(parents=True, exist_ok=True)
            branch = r.get("integration_branch") or "main"
            subprocess.run(["git", "init", "-q", "-b", branch, str(path)])
            say(f"  created {r['path']} (git init, branch {branch})")
            continue
        if path.exists() or not r.get("remote"):
            continue
        if assume_yes or yes(f"clone {r['remote']} into {r['path']}?", True):
            if DRY:
                say(f"  [dry-run] git clone {r['remote']} {r['path']}")
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            res = subprocess.run(["git", "clone", r["remote"], str(path)])
            if res.returncode != 0:
                say(f"  WARN clone failed for {r['name']} — clone it manually to {r['path']}")


def enrich(cfg):
    for r in cfg["repos"]:
        path = resolve(r["path"])
        if not path.exists():
            r["_missing"] = True
            continue
        r.pop("_missing", None)
        g = detect_git(path)
        r.setdefault("remote", g.get("remote", ""))
        if r.get("policy") in ("editable", "pr-only"):
            r.setdefault("integration_branch", g.get("default_branch") or "develop")
            r.setdefault("protected_branches", sorted({"main", "master", r["integration_branch"]}))
        stack, cmds, own, quiet = detect_stack(path)
        r["_stack"], r["_cmds"], r["_own"], r["_quiet"] = stack, cmds, own, quiet


def render_map(cfg):
    projects = cfg.get("projects", [])
    repos = cfg.get("repos", [])
    g = cfg.get("git", {})
    L = [f"{BEGIN} (generated by setup/setup_workspace.py {datetime.date.today()} — edit workspace.config.json, then re-run with --render) -->",
         "## 1. Workspace map", "",
         "**Projects:**", "",
         "| Project | Types | Work modes | Repos | Context dir |",
         "| --- | --- | --- | --- | --- |"]
    for p in projects:
        members = [f"`{n}`" for n in p.get("repos", [])] + [f"`{n}` (reference)" for n in p.get("reference_repos", [])]
        L.append(f"| `{p['name']}` — {p.get('description', '')} | {', '.join(p.get('types', [])) or 'not set'} | "
                 f"{', '.join(p.get('modes', []))} | {', '.join(members) or '—'} | `{ctx_dir(p)}/` |")
    L += ["", f"**Tickets in:** {cfg.get('source_language', '?')} · "
          f"**Stakeholder replies in:** {cfg.get('stakeholder_language', '?')}", "",
          "| Repo | Project | Role | Path | Modifiable? | Integration branch | Context |",
          "| --- | --- | --- | --- | --- | --- | --- |"]
    for r in repos:
        member, ref = repo_projects(cfg, r["name"])
        owners = ", ".join(member + [f"{n} (reference)" for n in ref]) or "—"
        L.append(f"| `{r['name']}` | {owners} | {ROLES.get(r['role'], ('?',))[0]} | `{r['path']}` | {r['policy']} — "
                 f"{POLICY_TEXT[r['policy']]} | {r.get('integration_branch', '—')} | `context/repos/{r['name']}.md` |")
    roles = {r["role"] for r in repos}
    L += ["", "**Ownership routing** — default repo for an item:"]
    if "frontend" in roles:
        L.append("- UI rendering, form state, client validation, navigation → frontend repo.")
    if "backend" in roles:
        L.append("- Data, business logic, API validation, SQL → backend repo. Both layers → fix the API first.")
    if "reports" in roles:
        L.append("- Report output → first prove the data the API ships is correct; only then is it report-side"
                 + (" (flag-only: surface, don't edit)." if any(r['role'] == 'reports' and r['policy'] == 'flag-only' for r in repos) else "."))
    if "database" in roles:
        L.append("- Column widths / nullability / constraints → database repo (read-only).")
    if "docs" in roles:
        L.append("- Domain meaning, specs, ER narrative → docs repo **first**, before grepping code.")
    if roles & {"legacy-frontend", "legacy-backend", "legacy-database"}:
        L.append("- **Reference implementation:** the legacy repos are the de-facto spec in defect mode "
                 "(AGENTS.md §2). Read-only; re-derive, never copy; cite file:line + recommendation; "
                 "check the deployed build's date/version when source and observed behavior disagree.")
    if any(p.get("reference_repos") for p in projects):
        L.append("- **Project reference repos** (`(reference)` in Projects): the de-facto spec for that project's "
                 "port work. Read them; don't edit them as part of that project's work, even when they are "
                 "editable for their own project.")
    have = {p["name"]: project_roles(cfg, p) for p in projects}
    missing = [r for r in ROLES if r != "other" and ROLES[r][3] and any(r not in v for v in have.values())]
    if missing:
        L += ["", "**Not registered** (agents fall back as noted):"]
        for r in missing:
            lacking = [n for n, v in have.items() if r not in v]
            scope = f" ({', '.join(lacking)})" if len(have) > 1 else ""
            L.append(f"- {ROLES[r][0]}{scope}: {ROLES[r][3]}.")
    L += ["", "**Git naming:**", "",
          "| Item type | Branch | Commit header | PR title |", "| --- | --- | --- | --- |",
          f"| defect | `{g.get('fix_branch', 'fix/{area}/{item}')}` | `{g.get('commit', '{area}: ({item}) {summary}')}` | `{g.get('pr_title', '[{ITEM}] {summary}')}` |",
          f"| change request | `{g.get('change_branch', 'change/{area}/{item}')}` | same | same |", "",
          "Placeholders: `{area}` = lowercase screen/module ID, `{item}` = lowercase item token, "
          "`{ITEM}` = display ID. Branch names use `[a-z0-9/-]` only.", ""]
    srcs = cfg.get("tracker", {}).get("sources", [])
    if srcs:
        L += ["**Work-item sources** (`python modules/tracker/fetch_items.py`):", ""]
        for s in srcs:
            L.append(f"- `{s.get('id_prefix') or '<number>'}…` → `{s['name']}` ({s['type']}) → `_work/items/{s['name']}.json`")
        L.append("- Mixed batches route by prefix; an ambiguous prefix → ask.")
        L.append("")
    L.append(END)
    return "\n".join(L)


def render_context(r):
    tpl = (ROOT / "context" / "repos" / "_TEMPLATE.md").read_text(encoding="utf-8")
    stack = "\n".join(f"- {s} (detected)" for s in r.get("_stack", [])) or "- <fill in>"
    if r.get("_own"):
        stack += "\n- Repo ships its own agent instructions: " + ", ".join(f"`{o}`" for o in r["_own"]) + " — read them too."
    cmds = "\n".join(f"- {c} (detected)" for c in r.get("_cmds", [])) or "- <fill in: dev, build, test, lint>"
    quiet = "\n".join(f"- {q} (detected — confirm the flags)" for q in r.get("_quiet", [])) or (
        "- <fill in: one test file with a dot/summary reporter; lint errors only; typecheck errors only>")
    vals = {"name": r["name"], "role_label": ROLES.get(r["role"], ("?",))[0], "policy": r["policy"],
            "path": r["path"], "remote": r.get("remote") or "—",
            "integration_branch": r.get("integration_branch", "—"),
            "protected_branches": ", ".join(r.get("protected_branches", [])) or "—",
            "detected_stack": stack, "detected_commands": cmds, "quiet_commands": quiet}
    out = tpl
    for k, v in vals.items():
        out = out.replace("{{" + k + "}}", v)
    if r.get("notes"):
        out = out.replace("## Tech stack", f"**Notes:** {r['notes']}\n\n## Tech stack", 1)
    if r["policy"] in ("read-only", "flag-only"):
        out = out.split("## Before submitting a change")[0] + (
            "## Rules\n- " + POLICY_TEXT[r["policy"]] + ".\n- Never run mutating git here "
            "(enforced by `.claude/hooks/repo_guard.py`).\n")
    return out


RULE_BANNER = "<!-- generated by setup/setup_workspace.py from context/repos/{name}.md — edit that file, then --render -->"


def render_rule(r, cfg):
    """Short path-scoped rule for one repo (.claude/rules/repo-<name>.md). Regenerated on every
    render. Only for repos inside the workspace: scoped globs are project-relative."""
    path = resolve(r["path"])
    try:
        rel = path.relative_to(ROOT).as_posix()
    except ValueError:
        say(f"  skipped .claude/rules for {r['name']}: path-scoped rules need the repo inside the workspace")
        return None
    L = ["---", "paths:", f'  - "{rel}/**"', "---", RULE_BANNER.format(name=r["name"]), "",
         f"# {r['name']} — {ROLES.get(r['role'], ('?',))[0]} ({r['policy']})", "",
         f"- Editable: {POLICY_TEXT[r['policy']]}.",
         f"- Integration branch: `{r.get('integration_branch', '—')}`; protected: "
         f"{', '.join(f'`{b}`' for b in r.get('protected_branches', [])) or '—'}.",
         f"- Full context (structure, ownership, defect patterns, quiet commands): `context/repos/{r['name']}.md` — "
         "read it before searching or running git here; this rule covers file access only."]
    member, ref = repo_projects(cfg, r["name"])
    for p in (find_project(cfg, n) for n in member):
        L.append(f"- Project: `{p['name']}` ({', '.join(p.get('types', [])) or 'type not set'}) — follow its profile "
                 f"(AGENTS.md §2); project context: `{ctx_dir(p)}/`.")
    for n in ref:
        L.append(f"- Reference for `{n}`: during `{n}` work, read it as the reference; don't edit it as part of that work.")
    if r["policy"] in ("read-only", "flag-only"):
        L.append("- **Never edit here and never run mutating git here** (enforced by `.claude/hooks/repo_guard.py`).")
    return "\n".join(L) + "\n"


def install_claude_dir():
    """Materialize .claude/ from claude-config/ (the template ships the agent config
    under a plain folder name so it can be copied by tools that refuse dot-folders).
    Existing files in .claude/ are never overwritten."""
    src = ROOT / "claude-config"
    dst = ROOT / ".claude"
    if not src.exists():
        return
    n = 0
    for f in src.rglob("*"):
        if f.is_dir() or "__pycache__" in f.parts:
            continue
        t = dst / f.relative_to(src)
        if t.exists():
            continue
        n += 1
        if DRY:
            say(f"  [dry-run] would install .claude/{f.relative_to(src)}")
            continue
        t.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, t)
    if n and not DRY:
        say(f"  installed {n} file(s) from claude-config/ into .claude/")


def public_cfg(cfg):
    c = json.loads(json.dumps(cfg))
    for r in c.get("repos", []):
        for k in [k for k in r if k.startswith("_")]:
            del r[k]
    return c


def apply(cfg):
    write(CONFIG, json.dumps(public_cfg(cfg), ensure_ascii=False, indent=2) + "\n")
    text = AGENTS.read_text(encoding="utf-8")
    block = render_map(cfg)
    if BEGIN in text and END in text:
        text = text[:text.index(BEGIN)] + block + text[text.index(END) + len(END):]
    else:
        text += "\n\n" + block + "\n"
    write(AGENTS, text)
    for r in cfg["repos"]:
        f = CTX / f"{r['name']}.md"
        if f.exists():
            say(f"  kept  {f.relative_to(ROOT)} (exists — edit by hand)")
        else:
            write(f, render_context(r))
    for r in cfg["repos"]:
        rule = render_rule(r, cfg)
        if rule is not None:
            write(ROOT / ".claude" / "rules" / f"repo-{r['name']}.md", rule)
    if not DRY:
        (ROOT / "secrets").mkdir(exist_ok=True)
        for d in ("_work", "reports"):
            (ROOT / d).mkdir(exist_ok=True)
    # interpreter name in hook commands
    py = python_cmd()
    sp = ROOT / ".claude" / "settings.json"
    s = sp.read_text(encoding="utf-8")
    s2 = re.sub(r'"command": "(?:python3?|py) ', f'"command": "{py} ', s)
    if s2 != s:
        write(sp, s2)
    # optional hooks → settings.local.json (machine-local)
    lp = ROOT / ".claude" / "settings.local.json"
    local = json.loads(lp.read_text(encoding="utf-8")) if lp.exists() else {}
    stop = local.setdefault("hooks", {}).setdefault("Stop", [])
    cmd = f'{py} "$CLAUDE_PROJECT_DIR/modules/usage-metrics/usage_tracker.py"'
    has = any(cmd in [x.get("command") for x in h.get("hooks", [])] for h in stop)
    if cfg.get("modules", {}).get("usage_metrics") and not has:
        stop.append({"hooks": [{"type": "command", "command": cmd, "timeout": 30}]})
        write(lp, json.dumps(local, indent=2) + "\n")
    elif not cfg.get("modules", {}).get("usage_metrics") and has:
        local["hooks"]["Stop"] = [h for h in stop if cmd not in [x.get("command") for x in h.get("hooks", [])]]
        write(lp, json.dumps(local, indent=2) + "\n")


def apply_extras(cfg):
    """Parity workspace rows + people roster seed (never overwrites existing files)."""
    pm = ROOT / "docs" / "parity.md"
    if cfg.get("modules", {}).get("parity") and pm.exists():
        text = pm.read_text(encoding="utf-8")
        head, sep, rest = text.partition("## Workspaces")
        body, sep2, tail = rest.partition("\n## Byte-identical")
        live = "\n".join(l for l in body.splitlines() if l.strip().startswith("|"))
        add = [f"| {w['name']} | {w['root']} | sibling workspace |" for w in cfg.get("parity_workspaces", [])
               if f"| {w['name']} |" not in live]
        if add and sep and sep2:
            body = body.rstrip("\n") + "\n" + "\n".join(add) + "\n"
            write(pm, head + sep + body + sep2 + tail)
    people = ROOT / "context" / "people.json"
    ex = ROOT / "context" / "people.example.json"
    if not people.exists() and ex.exists() and (cfg.get("modules", {}).get("usage_metrics") or cfg.get("modules", {}).get("pr_metrics")):
        write(people, ex.read_text(encoding="utf-8"))
        say("  seeded context/people.json from the example — replace with your team (canonical name + aliases)")


def summary(cfg):
    say("\n" + "=" * 72)
    say(" Registered repos")
    say("=" * 72)
    roles = set()
    for r in cfg["repos"]:
        roles.add(r["role"])
        state = "MISSING on disk" if r.get("_missing") else ("; ".join(r.get("_stack", [])[:2]) or "no stack detected")
        say(f"  ✓ {ROLES[r['role']][0]:<32} {r['name']:<18} {r['policy']:<10} {state}")
    for p in cfg.get("projects", []):
        say(f"\n  [{p['name']}] {', '.join(p.get('types', [])) or 'type not set'} → {ctx_dir(p)}/")
        prole = project_roles(cfg, p)
        skip = skipped_roles(project_profiles(p))
        for r in cfg["repos"]:
            if r["name"] in p.get("repos", []) and r["role"] in skip:
                say(f"  note: {r['name']} has role {r['role']}, which this project type does not use — kept, but no workflow reads it")
        for role in ROLES:
            if role not in prole and role != "other" and role not in skip:
                flag = "!" if role in PRIMARY else "·"
                say(f"  {flag} {ROLES[role][0]:<32} not provided — {ROLES[role][3]}")
        if not prole & set(PRIMARY) and "greenfield" not in p.get("types", []):
            say("\n  WARNING: neither a frontend nor a backend repo is registered.")
    for name, label, need in missing_required(cfg):
        say(f"\n  WARNING: [{name}] {label} needs a {need} repo — none registered.")
    say("\nNext steps:")
    say("  1. Review AGENTS.md §1 and fill the <fill in> parts of context/repos/*.md")
    say("     (structure, ownership, common defect patterns).")
    say("  2. Put credentials in secrets/ (gitignored): db-config.json, service-account.json.")
    say("  3. python setup/setup_workspace.py --install-global   (personal defaults, optional)")
    try:
        import tree_sitter_language_pack  # noqa: F401
    except Exception:
        say("  ·  code slices: pip install tree-sitter-language-pack   (exact function boundaries for"
            " modules/code-slice/cs.py; it falls back to a brace heuristic without it)")
    if cfg.get("modules", {}).get("usage_metrics"):
        say("  4. Restart the agent, send one message, then: python modules/usage-metrics/usage_tracker.py --check")
    if cfg.get("modules", {}).get("log_triage"):
        say("  ·  log triage: cd modules/log-triage && npm install   (only needed for symbolicate.js)")
    if cfg.get("modules", {}).get("parity"):
        say("  ·  parity: fill docs/parity.md tables, then python modules/parity/parity_check.py")
    if cfg.get("modules", {}).get("pr_metrics"):
        say("  ·  pr-metrics: gh auth login, then python modules/pr-metrics/fetch_pr_history.py --since <date>")
    nxt = {"greenfield": "fill {ctx}/architecture.md + conventions.md, then /scaffold-project, then /build <feature>",
           "maintenance": "fill {ctx}/environment.md + test-records.md, fetch the tracker, then /analyze <item-id>",
           "port": "fill {ctx}/port-conventions.md, build the area index, run port_status.py --discover --project {name}, then /port-feature <area>",
           "feature": "fill {ctx}/parity-baseline.md, write docs/specs/<feature>.md, then /analyze-change or /build"}
    i = 5
    for p in cfg.get("projects", []):
        for t in p.get("types", []):
            say(f"  {i}. [{p['name']}: {t}] " + nxt[t].format(ctx=ctx_dir(p), name=p["name"]))
            i += 1
        if not p.get("types"):
            say(f"  {i}. [{p['name']}] set a type: python setup/setup_workspace.py --set-type <type> --project {p['name']}")
            i += 1


# ───────────────────────── other commands ─────────────────────────

def check(cfg):
    bad = 0
    for r in cfg.get("repos", []):
        p = resolve(r["path"])
        ok = p.exists()
        msg = "ok" if ok else "MISSING"
        if ok and r.get("integration_branch") and (p / ".git").exists():
            has = run(["git", "rev-parse", "--verify", "--quiet", f"origin/{r['integration_branch']}"], cwd=p)
            if not has:
                msg += f" · origin/{r['integration_branch']} not found (git fetch?)"
        if ok and r.get("policy") in ("read-only", "flag-only") and (p / ".git").exists():
            dirty = run(["git", "status", "--porcelain"], cwd=p)
            if dirty:
                msg += " · WARNING: read-only repo has local changes"
        bad += not ok
        say(f"  {r['name']:<18} {r['policy']:<10} {r['path']:<40} {msg}")
    for p in cfg.get("projects", []):
        say(f"  project {p['name']}: {', '.join(p.get('types', [])) or 'type not set'}")
    for name, label, need in missing_required(cfg):
        bad += 1
        say(f"  MISSING ROLE: [{name}] {label} needs a {need} repo")
    for f in ("db-config.json", "service-account.json"):
        say(f"  secrets/{f:<22} {'present' if (ROOT / 'secrets' / f).exists() else 'absent'}")
    sys.exit(1 if bad else 0)


def install_global():
    src = (ROOT / "docs" / "global-defaults.md").read_text(encoding="utf-8")
    m = re.search(r"```markdown\n(.*?)```", src, re.S)
    if not m:
        sys.exit("global-defaults block not found")
    dest = Path.home() / ".claude" / "CLAUDE.md"
    if dest.exists():
        bak = dest.with_suffix(f".md.bak-{datetime.datetime.now():%Y%m%d%H%M%S}")
        if not DRY:
            shutil.copy2(dest, bak)
        say(f"  backup → {bak}")
    write(dest, m.group(1)) if not DRY else say(f"  [dry-run] would write {dest}")


# ───────────────────────── main ─────────────────────────

def main():
    global DRY
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", help="answers JSON (same shape as workspace.config.json)")
    ap.add_argument("--render", action="store_true", help="re-render from workspace.config.json")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--set-type", help="comma list: greenfield,maintenance,port,feature")
    ap.add_argument("--project", help="project that --set-type changes (needed when there are several)")
    ap.add_argument("--install-global", action="store_true")
    ap.add_argument("--yes", action="store_true", help="assume yes for clone prompts")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    DRY = a.dry_run
    existing = normalize(json.loads(CONFIG.read_text(encoding="utf-8"))) if CONFIG.exists() else {}
    install_claude_dir()
    if a.install_global:
        return install_global()
    if a.check:
        return check(existing)
    if a.set_type:
        if not existing:
            sys.exit("workspace.config.json not found — run setup first.")
        projects = existing.get("projects", [])
        if not a.project and len(projects) != 1:
            sys.exit("--set-type needs --project <name> (projects: " + ", ".join(p["name"] for p in projects) + ")")
        p = find_project(existing, a.project) if a.project else projects[0]
        p["types"] = parse_types(a.set_type)
        apply_type_defaults(existing)
        cfg = existing
        enrich(cfg)
        apply(cfg)
        apply_profile(cfg)
        apply_extras(cfg)
        return summary(cfg)
    if a.config:
        cfg = normalize(json.loads(Path(a.config).read_text(encoding="utf-8")))
        for r in cfg.get("repos", []):
            r.setdefault("policy", ROLES.get(r.get("role"), ROLES["other"])[1])
            r.setdefault("path", f"repos/{r['name']}")
        cfg.setdefault("git", {}).setdefault("push_namespaces", ["fix", "change", "feature"])
        for p in cfg.get("projects", []):
            p["types"] = parse_types(",".join(p.get("types", [])))
        apply_type_defaults(cfg, explicit=set(cfg.get("modules", {})))
    elif a.render:
        if not existing:
            sys.exit("workspace.config.json not found — run without --render first.")
        cfg = existing
        apply_type_defaults(cfg, explicit=set(cfg.get("modules", {})))
    else:
        cfg = interactive(existing)
    validate_projects(cfg)
    clone_missing(cfg, assume_yes=a.yes)
    enrich(cfg)
    apply(cfg)
    apply_profile(cfg)
    apply_extras(cfg)
    summary(cfg)


if __name__ == "__main__":
    main()
