# Lessons Catalog — failure modes and the rule that prevents each

Distilled from a long multi-repo bug-fix and port engagement (hundreds of items,
thousands of agent turns). Each entry: **failure mode → rule → where it is enforced**.
Add project-specific instances with item IDs under "Instances" as you hit them;
promote to AGENTS.md when a mode recurs.

| # | Failure mode | Rule | Enforced in |
|---|---|---|---|
| L1 | Static read of a runtime-state bug presented as root cause; fix shipped then reverted | Runtime-state symptoms cap at medium until observed; LOW → self-test before edit | analyze §7.3, fix §4 |
| L2 | Wrong code analyzed — the tracker's location field was mis-filed or blank | Identity check with literal strings from the report; recover blank locations first | analyze §5, AGENTS §4 |
| L3 | Evidence from the wrong DB instance / log environment / tenant / build | Name the environment on every observation; discriminate instances by data | AGENTS §2, db-query |
| L4 | "Tried it — didn't reproduce" on a trial that never executed (disabled button, form not dirty, missed click) | Assert every trial executed; "no error and no write" = invalid | AGENTS §2, verification §4 |
| L5 | Negative result generalized from one input path | Drive every commit path; confirm the field state arms the code path | verification §5.2 |
| L6 | Client change rejected by API schema or DB constraint | Cross-layer verifier before push | fix §9.5, fix-verifier |
| L7 | Fix revives dead code whose pre-existing defects ship as new bugs | Enumerate revived branches from the pre-fix file; audit value domains | fix §6 |
| L8 | Suppress-style fix leaves partner state stale (list refreshed, index/detail not) | Audit invariant partners of every write that still runs | fix §6 |
| L9 | Sweep keyed on names misses the same defect under other names; ships again months later | Zero-identifier defect sentence; key on roles/shape; control; open every candidate | fix §7 |
| L10 | Static sweep over-flags (many hits, few real) | Verify the full enabling mechanism per site; run the detector on a known-good sibling | fix §7.3 |
| L11 | Premise of the report was wrong (input-method artifact, by-design, upstream bad data) — commits later reverted | Verify premise against reference/real record before building or reverting | AGENTS §2 |
| L12 | "Regression" verdict from an intra-repo sibling or a dead legacy error branch | Claims about the reference need the reference artifact (and runtime if error-display) | AGENTS §2 |
| L13 | Reference source ≠ deployed reference build; hours spent explaining stale-binary behavior | Compare build date/version to the source clone first; decompile when they disagree | AGENTS §2 |
| L14 | Difference assumed to be a regression was a requested change | Check the spec-change registry; believe code evidence over registry labels | analyze §10 |
| L15 | Edits landed on someone else's branch / lost to a stash / anchors drifted | Re-check branch + status before each edit batch; re-verify anchors | AGENTS §3, fix §3, §5.0 |
| L16 | False "never merged" verdict from a stale checkout | `git fetch` before concluding | AGENTS §3 |
| L17 | Lint/typecheck "passed" without running (wrong arg, tool fetched and exited, output truncated) | Confirm the tool ran on the intended files; read full output | git-workflow 10.5.1, fix §9 |
| L18 | Production build fails on something lint/typecheck accept | Run the production build before push when the bundler transforms code | context/repos |
| L19 | PR body describes a mechanism the code doesn't have; cites non-existent line ranges | Verify every mechanism sentence and file:line against code read this session | fix §9.5 |
| L20 | Export files disagree with each other or carry stale verdicts | Integrity pass: re-read from artifacts, reconcile verdicts, scan for credentials | export |
| L21 | Credentials leaked into an export via a subagent | Grep written artifacts for secrets before confirming | export, AGENTS §3 |
| L22 | "While I'm here" ripple fixes inflate review burden | [A]/[B]/[C] prompt; one item per PR by default | fix §5.4 |
| L23 | Hypothesis of async race when the computed flag was never wired | Orphaned-flag check (two greps) first | analyze §7.4 |
| L24 | Stale state across dialog reopen in a long-lived store (reference built fresh per open) | Reset coverage in precondition table; reset on mount/unmount | analyze §6(e), port |
| L25 | Default-value divergence (empty→0, `.default(null)`, `??` defaults, hidden-field auto-fill) | Treat as a Tier-2 trigger | analyze §10 |
| L26 | Byte-width overflow for multibyte input despite character count fitting | Compute worst-case byte length vs column width | fix-verifier |
| L27 | Spawned sessions skip tracking steps; metrics silently incomplete | Reconcile after the fact; audit per item | area-loop, metrics |
| L28 | Probe changed the answer (duplicate module instance, forced state, synthetic events) | Liveness assertion; prefer real UI actions | verification §5.3 |
| L29 | Translating UI labels destroyed grep keys and invented names | Translate prose only; labels/identifiers verbatim | AGENTS §7 |
| L30 | Model routing drifted — almost everything ran on the top tier despite a cheaper default | Audit actual vs intended tier from the usage ledger | model-routing |
| L31 | Over-reading large spec/binary trees blew the context | Open by known path only; never glob spec trees | AGENTS §3 |
| L32 | An adversarial review round found a real defect in fixes already "verified" by their own session | Reviewer round is mandatory, attacks the claim, names its attempts | fix §9.5 |
| L33 | A large file came back truncated from an edit; the SyntaxError surfaced minutes later, far from the edit | Syntax-check every edited file immediately (PostToolUse hook) | `.claude/hooks/post_edit_check.py` |
| L34 | An alert/watch pipeline died (tunnel, SSH hop, process) and the quiet channel read as "no errors" | Dead-man's-switch healthcheck that alerts on state change | docs/workspace-topology.md, usage `--check` |
| L35 | A metrics hook was never installed on most machines; months of blank data before anyone noticed | Coverage check per person / session, not just "rows exist" | `usage_tracker.py --coverage` |
| L36 | One infrastructure incident fired on every endpoint and became dozens of "issues" | Fingerprint server errors on code + app frame + message, not endpoint; normalize ids/hashes/numbers | modules/log-triage/fingerprint.py |
| L37 | A bot overwrote triage columns people had filled in | Bots write only their own columns; upsert by stable key; keep own state to avoid double alerts | modules/tracker/README.md |
| L38 | Copies of a shared script drifted between sibling workspaces unnoticed | Parity registry + checker; edit the source-of-truth side and copy in the same change | docs/parity.md |
| L39 | One person appeared as several rows (email, nickname, first name) in every metric | Canonical name + aliases on day one | context/people.json |
| L40 | A long run ended on a progress update with work still open | TASKS.md checklist re-read before ending a turn; nudge limit | AGENTS.md §5 |
| L41 | Kept pushing a failing approach for several rounds | Two failures with the same approach → stop and re-plan | AGENTS.md §5 |

## Instances

Project instances are recorded as per-class files in `mistakes/` (AGENTS.md §10); link
a catalog row to its mistake file when one exists.
