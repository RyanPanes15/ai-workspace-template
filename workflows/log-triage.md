# Workflow: Log triage — distinct issues, delta-classified

**Tier:** standard @ medium. **Input:** a time window (default: since the last run) and
which log channels. **Read-only** — investigation only; no code changes, no tickets
filed (drafts only).

Goal: turn thousands of log lines into a short list of distinct problems, each marked
**NEW / STILL OPEN / FIXED IN CODE / WHITELISTED**, with evidence.

1. **Get the logs** for the window into `_work/logs/` (project-specific fetch; see
   `context/environment.md`). Name the environment (staging / prod / test instance) —
   every conclusion is scoped to it.
2. **Symbolicate client stacks** if the client ships minified bundles: pass
   `--symbolicate-maps <dir with the DEPLOYED build's *.js.map>`. Maps from another
   build resolve to wrong lines — check the bundle hash matches.
3. **Cluster:** `python modules/log-triage/triage_logs.py "_work/logs/<env>/**/*.log"
   --channel server` (and `--channel client`). Read the table, not the raw logs.
4. **Refresh code state** — `git fetch` and read the integration branch, not a stale
   checkout.
5. **Per NEW / ONGOING issue** (highest count first; stop at the time budget):
   - open the top app frame at the integration-branch HEAD (`cs.py trace` on the sample
     stack prints just those functions); `git log -L` / `git log
     --since=<first_seen>` on that region;
   - a commit after `last_seen` that plausibly fixes it → **FIXED IN CODE** (cite hash,
     and whether that commit is deployed — check deploy tags/dates; not deployed = still
     open in this environment);
   - otherwise **STILL OPEN** (seen before) or **NEW**; for each, one-line suspected cause
     tied to the frame, and whether it is already filed (search the tracker exports by
     endpoint / frame / message).
   - A null/empty-parameter validation error usually has a client-side cause (a value
     coerced to empty before the request) — name the likely caller via
     `area_index.py --callers`.
5b. **Escalation gate (early, not late).** This runs on the standard tier. The
   moment an issue needs real root-cause work — the top frame refutes the first
   suspected cause, the cause spans client + server, or the code at HEAD does not
   match the stack — stop investigating that issue here. Write what is known
   (fingerprint, frame, env, refuted hypothesis, files to open) into the drafted
   ticket and recommend `/analyze` in a deep session. Never keep looping on the
   standard tier, and never switch model mid-session.
6. **QUIET** issues (seen before, absent now) are not fixed until code says so — list
   them separately.
7. **Whitelist** only with a reason and a narrow scope (`--mute <fp> --note "…"`);
   never mute a whole screen/endpoint without a message or code.

Output: what I need from you (items to file / decisions) → summary counts → table per
status (fingerprint, count, first/last seen, frame, endpoint, cause, evidence, filed?)
→ drafted tickets for NEW items (not filed).
