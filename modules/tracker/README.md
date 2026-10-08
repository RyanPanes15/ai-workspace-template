# tracker module (optional)

Normalizes work items from CSV / JSON / Google Sheets / GitHub Issues into
`_work/items/<source>.json` so every workflow loads items the same way.

- Declare sources in `workspace.config.json` → `tracker.sources` (setup asks).
- Give each source a distinct `id_prefix` (e.g. `""` for bare numbers, `R`, `CR-`)
  so a mixed batch like `42,R7,CR-3` routes unambiguously.
- `tracker.enums` maps category/status codes to meanings for `item-scaffolder`;
  `tracker.translate_fields` lists free-text fields to translate.
- Run daily: `python modules/tracker/fetch_items.py` (best-effort; one failing
  source prints WARN and the rest continue). Exports are gitignored.

Source types: `csv`, `json`, `gsheet`, `github`, `redmine` (read-only REST; key in
`$REDMINE_API_KEY` or `secrets/redmine.json`).

**If you build a bot that writes back to a shared sheet or tracker:** the bot owns
only its own columns and never overwrites columns people edit (status, assignee,
triage notes); it upserts by a stable key, keeps its own state (last-seen update /
comment id) so it never double-alerts, and treats notification failures as
non-fatal. The fetcher here stays read-only by design.
