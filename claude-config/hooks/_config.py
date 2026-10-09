"""Shared helper for hooks: locate the workspace root and load workspace.config.json."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load_config():
    try:
        return json.loads((ROOT / "workspace.config.json").read_text(encoding="utf-8"))
    except Exception:
        return {}


def repo_paths(cfg):
    """(name, policy, resolved normalized path) of every registered repo."""
    out = []
    for r in cfg.get("repos", []):
        if r.get("path"):
            p = Path(r["path"])
            if not p.is_absolute():
                p = ROOT / p
            out.append((r.get("name", "?"), r.get("policy"), str(p.resolve()).replace("\\", "/").lower()))
    return out
