#!/usr/bin/env python3
"""Read-only SQL wrapper for agent investigations.

Usage:
  python modules/db-query/run_query.py "SELECT ..."            # active profile
  python modules/db-query/run_query.py --profile staging "SELECT ..."
  python modules/db-query/run_query.py --describe TABLE_NAME
  python modules/db-query/run_query.py --profiles               # list profiles

Config: secrets/db-config.json (gitignored), e.g.
  {"active": "dev",
   "profiles": {
     "dev": {"driver": "postgres", "host": "localhost", "port": 5432,
             "database": "app", "user": "readonly", "password": "..."},
     "legacy": {"driver": "oracle", "dsn": "localhost:1521/SERVICE",
                "user": "...", "password": "...", "thick": true}}}

Drivers: sqlite, postgres (psycopg2), mysql (pymysql), oracle (oracledb),
mssql (pyodbc). Only ONE statement starting with SELECT or WITH is accepted;
DML/DDL keywords outside string literals are rejected. Every run prints the
profile it used (so evidence always names its environment) and is appended to
_work/query-log.jsonl.
"""
import argparse
import datetime
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "secrets" / "db-config.json"
LOG = ROOT / "_work" / "query-log.jsonl"
FORBIDDEN = r"\b(INSERT|UPDATE|DELETE|MERGE|UPSERT|DROP|CREATE|ALTER|TRUNCATE|GRANT|REVOKE|CALL|EXEC|EXECUTE|BEGIN|COMMIT|ROLLBACK|LOCK|COPY|ATTACH|PRAGMA|SET)\b"


def strip_literals(sql):
    sql = re.sub(r"'(?:''|[^'])*'", "''", sql)
    sql = re.sub(r'"(?:""|[^"])*"', '""', sql)
    sql = re.sub(r"--[^\n]*", "", sql)
    return re.sub(r"/\*.*?\*/", "", sql, flags=re.S)


def check_readonly(sql):
    bare = strip_literals(sql).strip().rstrip(";").strip()
    if ";" in bare:
        sys.exit("REJECTED: multiple statements are not allowed.")
    if not re.match(r"^(SELECT|WITH)\b", bare, re.I):
        sys.exit("REJECTED: only SELECT / WITH queries are allowed.")
    m = re.search(FORBIDDEN, bare, re.I)
    if m:
        sys.exit(f"REJECTED: forbidden keyword '{m.group(1)}' outside a string literal.")
    return sql.strip().rstrip(";")


def connect(p):
    d = p["driver"]
    if d == "sqlite":
        import sqlite3
        return sqlite3.connect(f"file:{p['database']}?mode=ro", uri=True)
    if d == "postgres":
        import psycopg2
        c = psycopg2.connect(host=p["host"], port=p.get("port", 5432), dbname=p["database"],
                             user=p["user"], password=p.get("password"), sslmode=p.get("sslmode", "prefer"))
        c.set_session(readonly=True)
        return c
    if d == "mysql":
        import pymysql
        return pymysql.connect(host=p["host"], port=p.get("port", 3306), database=p["database"],
                               user=p["user"], password=p.get("password"))
    if d == "oracle":
        import oracledb
        if p.get("thick"):
            oracledb.init_oracle_client(lib_dir=p.get("lib_dir"))
        return oracledb.connect(user=p["user"], password=p["password"], dsn=p["dsn"])
    if d == "mssql":
        import pyodbc
        return pyodbc.connect(p["connection_string"], readonly=True)
    sys.exit(f"Unknown driver: {d}")


def describe_sql(driver, table):
    t = re.sub(r"[^A-Za-z0-9_.$]", "", table)
    if driver == "oracle":
        return ("SELECT column_name, data_type, data_length, char_used, nullable FROM all_tab_columns "
                f"WHERE table_name = UPPER('{t.split('.')[-1]}') ORDER BY column_id")
    if driver == "sqlite":
        return f"SELECT * FROM pragma_table_info('{t}')"
    return ("SELECT column_name, data_type, character_maximum_length, is_nullable FROM information_schema.columns "
            f"WHERE table_name = '{t.split('.')[-1]}' ORDER BY ordinal_position")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sql", nargs="?")
    ap.add_argument("--profile")
    ap.add_argument("--describe")
    ap.add_argument("--profiles", action="store_true")
    ap.add_argument("--limit", type=int, default=200)
    a = ap.parse_args()
    if not CONFIG.exists():
        sys.exit(f"Missing {CONFIG.relative_to(ROOT)} — copy modules/db-query/db-config.example.json there.")
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    if a.profiles:
        for k, v in cfg["profiles"].items():
            print(("* " if k == cfg.get("active") else "  ") + f"{k} ({v['driver']})")
        return
    name = a.profile or cfg.get("active")
    prof = cfg["profiles"][name]
    sql = describe_sql(prof["driver"], a.describe) if a.describe else a.sql
    if not sql:
        ap.error("SQL or --describe required")
    sql = check_readonly(sql)
    print(f"-- profile: {name} ({prof['driver']}) · {prof.get('label', '')}".rstrip(" ·"))
    conn = connect(prof)
    try:
        cur = conn.cursor()
        cur.execute(sql)
        cols = [c[0] for c in cur.description] if cur.description else []
        rows = cur.fetchmany(a.limit)
        print("\t".join(cols))
        for r in rows:
            print("\t".join("" if v is None else str(v) for v in r))
        more = cur.fetchone() is not None
        print(f"-- {len(rows)} row(s){' (truncated at --limit)' if more else ''}")
    finally:
        try:
            conn.rollback()
        except Exception:
            pass
        conn.close()
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": datetime.datetime.now().isoformat(timespec="seconds"),
                            "profile": name, "sql": sql, "rows": len(rows)}, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
