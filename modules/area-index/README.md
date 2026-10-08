# area-index module

`area_index.py build [--calls]` walks every registered repo once and maps each area
(screen / module / feature key) to its files by role; `--calls` adds which areas the
frontend references, so `area_index.py --callers X` gives the regression and
horizontal-sweep starting set. Configure recognition under `area_index` in
`workspace.config.json` (ID regex, suffix→role map, call regex). Rebuild after large
pulls or renames. Output: `_work/area-index.json`.
