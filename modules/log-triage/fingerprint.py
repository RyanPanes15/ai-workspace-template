"""Stable error fingerprints + whitelist matching (stdlib only, no I/O beyond reading
the whitelist file). Imported by triage_logs.py; unit-testable on its own.

Keys exclude line/column numbers, ids, UUIDs, hex hashes, IPs, build hashes and
timestamps. Server key: code + top app frame + normalized message (endpoint is display
only). Client key: top app frame + normalized message. Stale-chunk errors share one key.
Whitelist: message substring or exact code, optionally scoped; scope alone is rejected.
Rationale: modules/log-triage/README.md.
"""
import hashlib
import json
import re
from pathlib import Path

UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I)
HEX_RE = re.compile(r"\b(?:0x)?[0-9a-f]{8,}\b", re.I)
IP_RE = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}(?::\d+)?\b")
TS_RE = re.compile(r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(?::\d{2}(?:[.,]\d+)?)?(?:Z|[+-]\d{2}:?\d{2})?")
NUM_RE = re.compile(r"(?<![A-Za-z0-9])\d{3,}(?!\d)")   # keeps codes like E1001 / B0500 (letter-prefixed)
QUOTED_RE = re.compile(r"(['\"])(?:(?!\1).){1,200}\1")
STALE_CHUNK_RE = re.compile(r"Failed to fetch dynamically imported module|ChunkLoadError|Loading chunk \S+ failed|"
                            r"error loading dynamically imported module|Importing a module script failed", re.I)
VENDOR = ("node_modules", "site-packages", "dist-packages", "/vendor/", "\\vendor\\", "webpack/runtime",
          "<anonymous>", "internal/", "node:internal")
JS_FRAME = re.compile(r"\bat\s+(?:(?P<fn>[\w$.<>\[\] ?]+?)\s+\()?(?P<loc>[^()\s]+?\.(?:m?[jt]sx?|cjs|vue)):\d+(?::\d+)?\)?")
PY_FRAME = re.compile(r'File "(?P<loc>[^"]+)", line \d+, in (?P<fn>\S+)')
JAVA_FRAME = re.compile(r"\bat\s+(?P<fn>[\w$.]+)\((?P<loc>[\w$]+\.(?:java|kt|scala)):\d+\)")
CS_FRAME = re.compile(r"\bat\s+(?P<fn>[\w$.<>`]+)\(.*?\)\s+in\s+(?P<loc>.+?):line \d+")
BUNDLE_RE = re.compile(r"\b([A-Za-z][\w]*)[-.][0-9a-f]{6,}\.m?js\b")
ENDPOINT_RE = re.compile(r"\b(GET|POST|PUT|DELETE|PATCH)\s+(/[^\s|?\"']*)")
ERRWORD_RE = re.compile(r"(?:Uncaught\s+)?\b[\w.$]*(?:Error|Exception)\b(?::|\s).*")
LEVEL_RE = re.compile(r"\b(?:TRACE|DEBUG|INFO|WARN(?:ING)?|ERROR|FATAL|CRITICAL)\b")
BRACKET_CODE_RE = re.compile(r"\[[A-Z]{1,4}\d{2,6}[^\]]*\]")


def normalize(msg: str) -> str:
    if STALE_CHUNK_RE.search(msg):
        return "<stale-chunk: dynamic import failed after redeploy>"
    m = UUID_RE.sub("<id>", msg)
    m = TS_RE.sub("<ts>", m)
    m = IP_RE.sub("<ip>", m)
    m = HEX_RE.sub("<hex>", m)
    m = QUOTED_RE.sub(lambda x: x.group(1) + "…" + x.group(1) if len(x.group(0)) > 24 else x.group(0), m)
    m = NUM_RE.sub("<n>", m)
    return " ".join(m.split())[:300]


def top_app_frame(text: str):
    for ln in text.splitlines():
        if any(v in ln for v in VENDOR):
            continue
        for rx in (JS_FRAME, PY_FRAME, JAVA_FRAME, CS_FRAME):
            m = rx.search(ln)
            if m:
                loc = re.split(r"[\\/]", m.group("loc"))[-1]
                loc = re.sub(r"[-.][0-9a-f]{6,}(?=\.m?js$)", "", loc)   # drop build hash
                return f"{loc}:{(m.group('fn') or '?').strip()}"
    m = BUNDLE_RE.search(text)
    return m.group(1) if m else None


def error_line(text: str) -> str:
    """The error itself, without log prefix: timestamp, level, endpoint, bracketed code."""
    for ln in text.splitlines():
        m = ERRWORD_RE.search(ln)
        if m and not ln.lstrip().startswith("at "):
            return m.group(0).strip()
    first = next((ln for ln in text.splitlines() if ln.strip()), "")
    first = TS_RE.sub(" ", first)
    first = ENDPOINT_RE.sub(" ", first)
    first = BRACKET_CODE_RE.sub(" ", LEVEL_RE.sub(" ", first))
    return " ".join(first.replace("|", " ").split())


def compute(event_text: str, channel: str = "server", code_re=None):
    """Return dict(fingerprint, channel, code, frame, endpoint, message)."""
    msg = normalize(error_line(event_text))
    if msg.startswith("<stale-chunk"):
        key, frame, code = "stale-chunk", "dynamic-import", ""
    else:
        frame = top_app_frame(event_text) or "?"
        code = ""
        if code_re:
            m = re.search(code_re, event_text)
            code = m.group(1) if m and m.groups() else (m.group(0) if m else "")
        key = f"{channel}|{code}|{frame}|{msg}" if channel != "client" else f"client|{frame}|{msg}"
    em = ENDPOINT_RE.search(event_text)
    return {"fingerprint": hashlib.sha1(key.encode("utf-8")).hexdigest()[:12], "channel": channel,
            "code": code, "frame": frame, "endpoint": f"{em.group(1)} {em.group(2)}" if em else "",
            "message": msg}


def load_whitelist(path):
    p = Path(path)
    if not p.exists():
        return []
    entries = json.loads(p.read_text(encoding="utf-8"))
    ok = []
    for e in entries:
        if e.get("match_by") not in ("message", "code") or not str(e.get("pattern", "")).strip():
            raise ValueError(f"whitelist entry needs match_by message|code and a pattern (scope alone is not allowed): {e}")
        ok.append(e)
    return ok


def whitelisted(issue: dict, entries):
    """Return the matching entry or None."""
    for e in entries:
        scope = str(e.get("scope", "")).lower()
        if scope and scope not in (issue.get("endpoint", "") + " " + issue.get("frame", "")).lower():
            continue
        if e["match_by"] == "code" and issue.get("code") == e["pattern"]:
            return e
        if e["match_by"] == "message" and e["pattern"].lower() in issue.get("message", "").lower():
            return e
    return None
