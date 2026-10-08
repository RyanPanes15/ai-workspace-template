# log-triage module (optional)

Turns raw error logs into distinct issues. Stdlib Python, plus Node only for
symbolication.

- `triage_logs.py` — splits logs into events, fingerprints each error, applies the
  whitelist, and labels issues NEW / ONGOING / WHITELISTED / QUIET against the store in
  `_work/log-triage/issues.json`. `--list`, `--mute <fp> --note`, `--json`.
- `fingerprint.py` — the fingerprint and whitelist rules (read its docstring: server
  errors key on code + app frame + message, not endpoint; stale-chunk errors collapse;
  a scope alone never whitelists).
- `symbolicate.js` — minified stack → original file/line/function using the deployed
  build's source maps (`npm install` here once).
- `whitelist.example.json` — copy to `context/log-whitelist.json`.

Configure event boundaries / error filter / code regex under `log_triage` in
`workspace.config.json`. Used by `/log-triage` (`workflows/log-triage.md`).

**Why the fingerprint rules are what they are**
- Anything that varies between occurrences of one bug (line numbers, ids, hashes,
  timestamps) would split one bug into many issues, so it is normalized away.
- Server errors leave the endpoint out of the key: one infrastructure incident (pool
  exhausted, dead connection) fires the same code/frame/message on every endpoint and
  should be one issue, not dozens.
- Stale-chunk errors after a redeploy fail on whichever screen the user was on; they are
  one deployment issue.
- A scope-only whitelist entry would mute a whole screen and hide real bugs.

**Pattern worth copying for a live pipeline** (not shipped here): tail → fingerprint →
alert once per fingerprint → a bot-owned triage sheet where the bot writes only its own
columns and people own status/assignee → a dead-man's-switch healthcheck that alerts on
state change when the watcher, tunnel or SSH hop dies (a quiet channel looks exactly
like "no errors").
