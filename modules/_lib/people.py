"""Canonical person names from context/people.json (so one person = one row everywhere).

people.json:
  {"people": [
     {"name": "Ana", "role": "dev", "aliases": ["ana.reyes@corp.com", "ana.reyes", "areyes", "Ana R"]},
     {"name": "Ben", "role": "tester", "aliases": ["ben@corp.com"]}
  ]}
Matching is case-insensitive on the full value, the email local-part, and the first
token. Unknown values come back unchanged (and are worth adding as aliases).
Decide each person's canonical name on day one — every later variant costs a manual fix.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_CACHE = None


def roster(path=None):
    global _CACHE
    if _CACHE is None:
        p = Path(path) if path else ROOT / "context" / "people.json"
        _CACHE = json.loads(p.read_text(encoding="utf-8")).get("people", []) if p.exists() else []
    return _CACHE


def canon(value, path=None):
    if not value:
        return value
    v = str(value).strip().lower()
    keys = {v, v.split("@")[0], v.split()[0] if v.split() else v}
    for person in roster(path):
        names = {person["name"].lower(), *[a.lower() for a in person.get("aliases", [])]}
        names |= {n.split("@")[0] for n in list(names)}
        if keys & names:
            return person["name"]
    return value
