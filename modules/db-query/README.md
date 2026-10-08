# db-query module (optional)

Read-only SQL wrapper used by `/db-query` and the analyze workflow.

1. `pip install` the driver you need: `psycopg2-binary`, `pymysql`, `oracledb`, `pyodbc`.
2. Copy `db-config.example.json` → `secrets/db-config.json` (gitignored) and fill it in.
   Use a **read-only DB user** — the wrapper's SELECT check is a second line of defense,
   not the first.
3. Add one profile per instance and give each a `label` that says who uses it
   (dev stack vs testers). Every output starts with the profile line so evidence
   always names its environment.
4. Test: `python modules/db-query/run_query.py "SELECT 1"` (Oracle: `SELECT 1 FROM DUAL`).
