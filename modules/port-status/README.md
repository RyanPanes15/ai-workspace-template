# port-status module (port projects)

`port_status.py` reads `context/port-map.csv` (one row per area being ported) and
reports progress, validates rows and paths (`--check`), lists reference areas that have
no row yet (`--discover`, using the area index), and updates rows (`--add`, `--set`).
`verified`/`done` require the logic-inventory file the completeness verifier checked,
so "done" always has evidence behind it. Stdlib only.
