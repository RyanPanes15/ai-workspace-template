#!/usr/bin/env python3
"""Decode compressed API payloads (base64 + zlib/gzip/deflate) into readable JSON.

Some APIs return compressed bodies such as {"response": "eJx..."} (base64 of zlib).
Network captures, server logs and tester evidence therefore show opaque strings.

Usage:
  python modules/payload-decode/decode_response.py capture.json           # file with {"response": "..."}
  python modules/payload-decode/decode_response.py -                       # stdin (paste, then Ctrl-Z/Ctrl-D)
  python modules/payload-decode/decode_response.py --text "eJx..."          # raw base64 string
  python modules/payload-decode/decode_response.py capture.har --url /api/orders   # every matching HAR entry
  python modules/payload-decode/decode_response.py f.json --path results.0.name   # print one field
  python modules/payload-decode/decode_response.py f.json --out _work/decoded.json --summary

Behavior:
  * Auto-detects the payload: a JSON object's "response" key (or --key), any string
    value that decodes, or the whole input as base64.
  * Tries zlib, gzip, then raw deflate; reports which one worked.
  * --summary prints message/code/counts and the keys/row count of `results`
    instead of the whole body (keeps the agent's context small).
"""
import argparse
import base64
import binascii
import gzip
import json
import re
import sys
import zlib
from pathlib import Path

B64 = re.compile(r"^[A-Za-z0-9+/=_\-\s]{16,}$")


def inflate(data: bytes):
    for name, fn in (("zlib", zlib.decompress),
                     ("gzip", gzip.decompress),
                     ("deflate", lambda b: zlib.decompress(b, -15))):
        try:
            return name, fn(data)
        except Exception:
            continue
    return None, None


def decode_b64(s: str):
    s = re.sub(r"\s+", "", s)
    s += "=" * (-len(s) % 4)
    for dec in (base64.b64decode, base64.urlsafe_b64decode):
        try:
            return dec(s)
        except (binascii.Error, ValueError):
            continue
    return None


def decode_string(s: str):
    """Return (method, python_object_or_text) or (None, None)."""
    if not isinstance(s, str) or not B64.match(s.strip()):
        return None, None
    raw = decode_b64(s)
    if raw is None:
        return None, None
    method, out = inflate(raw)
    if out is None:
        return None, None
    text = out.decode("utf-8", errors="replace")
    try:
        return method, json.loads(text)
    except json.JSONDecodeError:
        return method, text


def decode_any(text: str, key=None):
    text = text.strip()
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        obj = None
    if isinstance(obj, dict):
        keys = [key] if key else (["response"] + [k for k in obj if k != "response"])
        for k in keys:
            if k in obj:
                m, v = decode_string(obj[k])
                if m:
                    return m, k, v
        return None, None, obj  # already plain JSON
    if isinstance(obj, str):
        text = obj
    m, v = decode_string(text)
    return m, None, v


def pick(obj, path):
    for part in path.split("."):
        if isinstance(obj, list):
            obj = obj[int(part)]
        elif isinstance(obj, dict):
            obj = obj.get(part)
        else:
            return None
    return obj


def summarize(v):
    if not isinstance(v, dict):
        return v
    s = {k: v.get(k) for k in ("message", "error", "code", "totalCount", "totalPage", "currentPage") if k in v}
    r = v.get("results")
    if isinstance(r, list):
        s["results"] = f"list[{len(r)}]" + (f" keys={list(r[0].keys())[:25]}" if r and isinstance(r[0], dict) else "")
    elif isinstance(r, dict):
        s["results"] = {k: (f"list[{len(x)}]" if isinstance(x, list) else x) for k, x in list(r.items())[:40]}
    return s


def emit(v, args):
    if args.path:
        v = pick(v, args.path)
    if args.summary:
        v = summarize(v)
    out = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False, indent=None if args.compact else 2)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(out, encoding="utf-8")
        print(f"-- written to {args.out} ({len(out)} chars)")
    else:
        print(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", nargs="?", help="file path, HAR file, or - for stdin")
    ap.add_argument("--text", help="raw base64 payload")
    ap.add_argument("--key", help="JSON key holding the payload (default: response, then any)")
    ap.add_argument("--url", help="HAR only: substring the request URL must contain")
    ap.add_argument("--path", help="dot path to print, e.g. results.0.id")
    ap.add_argument("--summary", action="store_true")
    ap.add_argument("--compact", action="store_true")
    ap.add_argument("--out")
    a = ap.parse_args()

    if a.text:
        text = a.text
    elif a.input in (None, "-"):
        text = sys.stdin.read()
    else:
        p = Path(a.input)
        text = p.read_text(encoding="utf-8-sig", errors="replace")
        if p.suffix.lower() == ".har":
            har = json.loads(text)
            n = 0
            for e in har.get("log", {}).get("entries", []):
                url = e.get("request", {}).get("url", "")
                if a.url and a.url not in url:
                    continue
                body = (e.get("response", {}).get("content") or {}).get("text") or ""
                if (e.get("response", {}).get("content") or {}).get("encoding") == "base64":
                    body = base64.b64decode(body).decode("utf-8", "replace")
                m, k, v = decode_any(body, a.key)
                print(f"\n### {e.get('request', {}).get('method')} {url}  [{m or 'plain'}]")
                emit(v, a)
                n += 1
            print(f"\n-- {n} entr{'y' if n == 1 else 'ies'} decoded")
            return
    m, k, v = decode_any(text, a.key)
    if m is None and v is None:
        sys.exit("Could not decode: not base64 + zlib/gzip/deflate, and not JSON.")
    print(f"-- decoded via {m or 'none (plain JSON)'}" + (f" from key '{k}'" if k else ""), file=sys.stderr)
    emit(v, a)


if __name__ == "__main__":
    main()
