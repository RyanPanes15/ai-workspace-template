# Onboarding checklist (new developer)

`README.md` is the reference; this is the checklist. Target: half a day, paired for B4.

## A. Before day 1 (admin)
- [ ] AI tool seat provisioned; note plan limits (weekly caps affect model routing).
- [ ] Company email used for the seat, git hosting, and tracker access (metrics join on it).
- [ ] Access to every repo in `workspace.config.json` and every tracker source.
- [ ] Read-only credentials for DB / service accounts ready — shared out of band.
- [ ] Decide the display name used in trackers and metrics; use it consistently.

## B. Day 1
### B1. Workspace (~30 min)
- [ ] Clone this workspace; run `python setup/setup_workspace.py --check`.
- [ ] Missing repos → `python setup/setup_workspace.py --yes --render` clones them.
- [ ] `python setup/setup_workspace.py --install-global` (personal defaults).
- [ ] Credentials into `secrets/`; never commit them.
### B2. Modules (~20 min, only those enabled)
- [ ] Tracker: `python modules/tracker/fetch_items.py` → every source prints OK.
      A WARN on one source usually means it was never shared with the service account.
- [ ] DB: `python modules/db-query/run_query.py "SELECT 1"` prints the profile line.
- [ ] Usage ledger: restart the agent, send a message, **confirm a line appears in
      `reports/usage.jsonl`**. This fails silently if skipped.
### B3. Read (~30 min)
- [ ] AGENTS.md §2 (behavior contract, evidence rules) and §3 (guardrails).
- [ ] `docs/lessons-catalog.md` — the failure modes the workflows are built to prevent.
### B4. Walkthrough (~60 min, paired)
- [ ] Watch `/analyze` then `/fix` on a real item, including the reviewer round.
- [ ] Understand which integration branch each repo's PRs target.
- [ ] Understand the horizontal sweep and why it is the most common review finding.
- [ ] Run one item end-to-end yourself, including the PR.
### B5. Conventions
- [ ] Branch / commit / PR naming (AGENTS.md §1).
- [ ] Manual testing is yours: a regression run you did not watch is not a regression run.

## C. First week
- [ ] One review round on your own PR end to end.
- [ ] Add one entry to a `context/repos/*.md` "common defect patterns" section.
