# Workflow: Read-only DB investigation

**Tier:** standard @ medium (escalate for hard reproducer searches).
**Input:** item ID + an open question, or `find repro data for <UI state>`.
**Tool:** `python modules/db-query/run_query.py "<SELECT …>"` — the wrapper rejects
anything that is not a single SELECT/WITH. Never bypass it.

First output line is the mode banner: `Investigation mode` or `Reproducer-data mode`.

## Before any SQL
- **Which instance?** State it. Discriminate instances with data (`COUNT(*)` +
  `MAX(pk)` on a churning table, or the reporter's own record) — instance/service
  names are often identical everywhere. Pair the DB with the matching log environment.
- Load the item context and the precondition table from the analysis, if any.
- Read curated schema knowledge (ER notes, sentinel-value catalog) before inferring
  joins from column names.

## Investigation mode
1. Identify tables (schema snapshot / schema repo / backend queries for the endpoint).
   `cs.py sql <TABLE|PROC>` prints one object's DDL or body; `cs.py sql --column COL`
   lists the tables and code that carry a column.
2. Query to confirm or refute the hypothesis: flag values, row counts, sample records,
   column shape.
3. Classify: code defect · data defect · environment · inconclusive.
   **A data defect is only concluded after a code cause is ruled out** (actual error
   log + reference comparison). Draft any correction as a scoping SELECT; escalate.
4. Summary: queries run, results, classification, confidence.

## Reproducer-data mode
1. **Trace UI invariants → column predicates** first (the precondition table). No
   "query the table that owns the column" shortcut — incomplete traces return rows
   that don't reproduce.
2. Find the parent list/search screen's own query; compose base query + UI filters.
3. **Reachability before sampling:** `COUNT(*)` first. 0 or millions → composition wrong.
4. Fallback ladder when it falls through: relax one predicate at a time; check the
   server-side branch selector; check default/sentinel handling.
5. Sample by recency (`ORDER BY <updated_at> DESC`), exclude sentinel values per the
   catalog, **avoid forward date windows** (historical data skew zeroes results).
6. Output **user-facing codes** a tester can type, not internal sequence IDs.

## Hard rules
SELECT only · mode banner · trace before SQL · count before sample · user-facing IDs
· name the instance on every result · new sentinel discoveries are proposed, not
written, to the catalog.
