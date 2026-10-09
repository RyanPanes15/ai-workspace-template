"""Tests for multi-project workspaces (docs/specs/multi-project-workspace.md).

Run: python -m unittest discover -s setup/tests
Each test copies the setup script, profiles and hooks into a temp workspace and runs them there.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[2]


def make_workspace():
    root = Path(tempfile.mkdtemp(prefix="ws-"))
    for d in ("setup", "profiles", "modules/port-status", "claude-config/hooks"):
        shutil.copytree(SRC / d, root / d, ignore=shutil.ignore_patterns("__pycache__", "tests"))
    (root / "context" / "repos").mkdir(parents=True)
    shutil.copy2(SRC / "context" / "repos" / "_TEMPLATE.md", root / "context" / "repos" / "_TEMPLATE.md")
    # an installed workspace has .claude/; the template ships claude-config/
    cfg = SRC / ".claude" if (SRC / ".claude" / "settings.json").exists() else SRC / "claude-config"
    (root / ".claude").mkdir()
    shutil.copy2(cfg / "settings.json", root / ".claude" / "settings.json")
    shutil.copytree(cfg / "hooks", root / ".claude" / "hooks", ignore=shutil.ignore_patterns("__pycache__"))
    agents = (SRC / "AGENTS.md").read_text(encoding="utf-8")
    (root / "AGENTS.md").write_text(agents, encoding="utf-8")
    return root


def run(root, *args, stdin=None):
    return subprocess.run([sys.executable, *args], cwd=root, capture_output=True, text=True,
                          encoding="utf-8", input=stdin, env={**os.environ, "PYTHONIOENCODING": "utf-8"})


def setup(root, *args):
    return run(root, "setup/setup_workspace.py", *args)


def write_answers(root, cfg):
    p = root / "answers.json"
    p.write_text(json.dumps(cfg), encoding="utf-8")
    for r in cfg["repos"]:
        (root / r["path"]).mkdir(parents=True, exist_ok=True)
    return p


TWO_PROJECTS = {
    "source_language": "English",
    "stakeholder_language": "English",
    "projects": [
        {"name": "knowledge", "description": "site", "types": ["greenfield"], "repos": ["site"]},
        {"name": "aniyomi-wn", "description": "android", "types": ["feature", "maintenance"],
         "repos": ["aniyomi", "aniyomi-docs"]},
        {"name": "inkwell", "description": "desktop", "types": ["port", "feature"],
         "repos": ["inkwell", "aniyomi-docs"], "reference_repos": ["aniyomi"]},
    ],
    "repos": [
        {"name": "site", "role": "frontend", "path": "repos/site", "policy": "editable", "integration_branch": "master"},
        {"name": "aniyomi", "role": "frontend", "path": "repos/aniyomi", "policy": "editable", "integration_branch": "main"},
        {"name": "inkwell", "role": "frontend", "path": "repos/inkwell", "policy": "editable", "integration_branch": "main"},
        {"name": "aniyomi-docs", "role": "docs", "path": "repos/aniyomi-docs", "policy": "editable", "integration_branch": "main"},
    ],
    "modules": {"usage_metrics": False},
}


class TwoProjects(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = make_workspace()
        res = setup(cls.root, "--config", str(write_answers(cls.root, json.loads(json.dumps(TWO_PROJECTS)))), "--yes")
        assert res.returncode == 0, res.stdout + res.stderr
        cls.cfg = json.loads((cls.root / "workspace.config.json").read_text(encoding="utf-8"))
        cls.agents = (cls.root / "AGENTS.md").read_text(encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.root, ignore_errors=True)

    def project(self, name):
        return next(p for p in self.cfg["projects"] if p["name"] == name)

    def test_ac1_modes_per_project(self):
        self.assertEqual(self.project("knowledge")["modes"], ["build"])
        self.assertEqual(self.project("inkwell")["modes"], ["port", "change"])
        self.assertNotIn("project", self.cfg)

    def test_ac3_projects_table_and_profile_once(self):
        self.assertTrue("**Projects:**" in self.agents, "**Projects:**")
        self.assertTrue("| Repo | Project | Role |" in self.agents, "| Repo | Project | Role |")
        self.assertEqual(self.agents.count("### Feature addition on an existing port"), 1)
        self.assertEqual(self.agents.count("### Port migration (port mode)"), 1)
        self.assertTrue("`context/projects/inkwell/`" in self.agents, "`context/projects/inkwell/`")

    def test_ac4_rule_names_project(self):
        rule = (self.root / ".claude" / "rules" / "repo-site.md").read_text(encoding="utf-8")
        self.assertIn("Project: `knowledge`", rule)
        self.assertIn("context/projects/knowledge/", rule)

    def test_ac6_shared_and_reference_repo(self):
        row = next(l for l in self.agents.splitlines() if l.startswith("| `aniyomi` |"))
        self.assertIn("aniyomi-wn", row)
        self.assertIn("inkwell (reference)", row)
        docs_row = next(l for l in self.agents.splitlines() if l.startswith("| `aniyomi-docs` |"))
        self.assertIn("aniyomi-wn, inkwell", docs_row)
        rule = (self.root / ".claude" / "rules" / "repo-aniyomi.md").read_text(encoding="utf-8")
        self.assertIn("Reference for `inkwell`", rule)

    def test_ac7_scaffold_per_project(self):
        ctx = self.root / "context" / "projects"
        self.assertTrue((ctx / "knowledge" / "architecture.md").exists())
        self.assertTrue((ctx / "inkwell" / "port-map.csv").exists())
        self.assertTrue((ctx / "inkwell" / "parity-baseline.md").exists())
        self.assertTrue((ctx / "aniyomi-wn" / "parity-baseline.md").exists())
        self.assertFalse((self.root / "context" / "architecture.md").exists())
        self.assertTrue((self.root / "docs" / "specs" / "_TEMPLATE.md").exists())

    def test_ac5_check_accepts_reference_repos(self):
        res = setup(self.root, "--check")
        self.assertEqual(res.returncode, 0, res.stdout)
        self.assertNotIn("MISSING ROLE", res.stdout)

    def test_ac5_port_status_uses_project(self):
        (self.root / "_work").mkdir(exist_ok=True)
        (self.root / "_work" / "area-index.json").write_text(json.dumps(
            {"index": {"AREA1": ["aniyomi"], "AREA2": ["inkwell"]}}), encoding="utf-8")
        res = run(self.root, "modules/port-status/port_status.py", "--project", "inkwell", "--discover")
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertIn("UNMAPPED AREA1", res.stdout)
        self.assertNotIn("AREA2", res.stdout)
        res = run(self.root, "modules/port-status/port_status.py")
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)


class SetType(unittest.TestCase):
    def setUp(self):
        self.root = make_workspace()
        res = setup(self.root, "--config", str(write_answers(self.root, json.loads(json.dumps(TWO_PROJECTS)))), "--yes")
        assert res.returncode == 0, res.stdout + res.stderr

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_ac8_set_type_needs_project(self):
        res = setup(self.root, "--set-type", "maintenance")
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("knowledge", res.stdout + res.stderr)

    def test_ac8_set_type_one_project(self):
        res = setup(self.root, "--set-type", "maintenance", "--project", "knowledge")
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        cfg = json.loads((self.root / "workspace.config.json").read_text(encoding="utf-8"))
        types = {p["name"]: p["types"] for p in cfg["projects"]}
        self.assertEqual(types["knowledge"], ["maintenance"])
        self.assertEqual(types["inkwell"], ["port", "feature"])


class LegacySingleProject(unittest.TestCase):
    def test_ac2_old_shape_is_rewritten(self):
        root = make_workspace()
        try:
            old = {"project": {"name": "knowledge-check", "description": "site", "source_language": "English",
                               "stakeholder_language": "English", "types": ["greenfield"]},
                   "repos": [{"name": "site", "role": "frontend", "path": "repos/site", "policy": "editable",
                              "integration_branch": "master"}],
                   "modules": {"usage_metrics": False}}
            write_answers(root, old)
            (root / "workspace.config.json").write_text(json.dumps(old), encoding="utf-8")
            res = setup(root, "--render")
            self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
            cfg = json.loads((root / "workspace.config.json").read_text(encoding="utf-8"))
            self.assertNotIn("project", cfg)
            self.assertEqual(cfg["projects"][0]["name"], "knowledge-check")
            self.assertEqual(cfg["projects"][0]["repos"], ["site"])
            self.assertEqual(cfg["projects"][0]["modes"], ["build"])
            self.assertEqual(cfg["source_language"], "English")
            agents = (root / "AGENTS.md").read_text(encoding="utf-8")
            self.assertEqual(agents.count("### Fresh new code project (build mode)"), 1)
            self.assertTrue((root / "context" / "projects" / "knowledge-check" / "architecture.md").exists())
        finally:
            shutil.rmtree(root, ignore_errors=True)


class UsageHook(unittest.TestCase):
    def test_render_adds_stop_hook_once(self):
        root = make_workspace()
        try:
            cfg = json.loads(json.dumps(TWO_PROJECTS))
            cfg["modules"]["usage_metrics"] = True
            setup(root, "--config", str(write_answers(root, cfg)), "--yes")
            res = setup(root, "--render")
            self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
            local = json.loads((root / ".claude" / "settings.local.json").read_text(encoding="utf-8"))
            self.assertEqual(len(local["hooks"]["Stop"]), 1)
        finally:
            shutil.rmtree(root, ignore_errors=True)


def junction(link, target):
    subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)], check=True, capture_output=True)


@unittest.skipUnless(os.name == "nt", "directory junctions are Windows-only")
class RepoGuard(unittest.TestCase):
    def setUp(self):
        self.root = make_workspace()
        self.ext = Path(tempfile.mkdtemp(prefix="ext-"))

    def tearDown(self):
        for p in (self.root / "repos").glob("*"):
            os.rmdir(p) if p.is_junction() else None
        shutil.rmtree(self.root, ignore_errors=True)
        shutil.rmtree(self.ext, ignore_errors=True)

    def guard(self, repos, file_path):
        (self.root / "workspace.config.json").write_text(json.dumps({"repos": repos}), encoding="utf-8")
        data = {"tool_name": "Edit", "tool_input": {"file_path": str(file_path)}, "cwd": str(self.root)}
        res = run(self.root, ".claude/hooks/repo_guard.py", stdin=json.dumps(data))
        return "deny" in res.stdout

    def test_ac10_junctioned_read_only_repo_is_protected(self):
        (self.ext / "ref").mkdir()
        (self.root / "repos").mkdir()
        junction(self.root / "repos" / "ref", self.ext / "ref")
        repos = [{"name": "ref", "role": "legacy-frontend", "path": "repos/ref", "policy": "read-only"}]
        self.assertTrue(self.guard(repos, self.root / "repos" / "ref" / "a.kt"))
        self.assertTrue(self.guard(repos, self.ext / "ref" / "a.kt"))
        data = {"tool_name": "Bash", "tool_input": {"command": "git -C repos/ref commit -m x"}, "cwd": str(self.root)}
        self.assertIn("deny", run(self.root, ".claude/hooks/repo_guard.py", stdin=json.dumps(data)).stdout)
        data["tool_input"]["command"] = "git -C repos/ref status"
        self.assertNotIn("deny", run(self.root, ".claude/hooks/repo_guard.py", stdin=json.dumps(data)).stdout)

    def test_ac10_most_specific_repo_wins(self):
        (self.ext / "inner").mkdir()
        (self.root / "repos").mkdir()
        junction(self.root / "repos" / "umbrella", self.ext)
        junction(self.root / "repos" / "inner", self.ext / "inner")
        repos = [{"name": "umbrella", "role": "docs", "path": "repos/umbrella", "policy": "read-only"},
                 {"name": "inner", "role": "frontend", "path": "repos/inner", "policy": "editable"}]
        self.assertFalse(self.guard(repos, self.root / "repos" / "inner" / "a.kt"))
        self.assertFalse(self.guard(repos, self.root / "repos" / "umbrella" / "inner" / "a.kt"))
        self.assertTrue(self.guard(repos, self.root / "repos" / "umbrella" / "README.md"))
        repos[0]["policy"], repos[1]["policy"] = "editable", "read-only"
        self.assertTrue(self.guard(repos, self.root / "repos" / "umbrella" / "inner" / "a.kt"))


if __name__ == "__main__":
    unittest.main()
