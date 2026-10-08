# Workflow: Review a pull request — merge-blocking problems only

**Tier:** deep @ high. **Input:** PR number / URL / branch. **Read-only**: no checkout,
no edits, no posted comments — draft the review text for the developer.

The bar: **list only problems you would block the merge for. For each one, give the
file and line, why it's wrong, and how to show it fails.** Style, naming and "could be
cleaner" are not findings.

0. Read `mistakes/INDEX.md`; each matching file is a check to run against this PR.
1. **Load.** `gh pr view <n> --json title,body,baseRefName,headRefName,files,commits`,
   `gh pr diff <n>`, `git fetch origin <base> <head>`. Read the repo's
   `context/repos/<name>.md` once. Read files at the head with `git show origin/<head>:<path>`; for the changed
   functions only, `cs.py diff <repo> origin/<base>...origin/<head>`.
2. **Find the claim.** Load the linked work item (branch/title token) and any prior
   analysis; restate the PR's claim in one sentence in the reporter's terms.
3. **Base branch** matches the workspace map; a wrong base is blocking.
4. **Check, stopping once the blocking set is found (don't pad):**
   - the diff produces the claimed behavior on the reported input path (walk the other
     commit paths on paper: type / picker / paste / clear / programmatic);
   - cross-layer: dispatch `fix-verifier` for any value newly sent to an endpoint;
   - revived code and, for suppress-style changes, invariant partners;
   - callers of every changed module/shared component (`area_index.py --callers`);
   - reference-parity claims backed by the reference artifact;
   - PR-body mechanism sentences and file:line citations match the diff;
   - guardrail violations: read-only/flag-only repos edited, secrets, author names,
     amended/force-pushed history, unrelated files;
   - lint via `modules/lint-gate` only if CI did not run it.
5. **Verify each finding** by constructing the failing input or sequence. If you cannot
   say how to show it fails, it is a QUESTION, not a finding.

Output:
```
PR #<n> — <title>   base ← head   item: <ID|none>
Claim: <one sentence>
BLOCKING (<count>)
1. <file>:<line> — <what is wrong>
   Why:   <consequence>
   Shows: <input / steps / test that makes it fail>
(If none) BLOCKING (0) — tried: <checks actually run, one line each>
QUESTIONS (max 3): <file>:<line> — <what would decide it>
Draft review comment: <paste-ready, targets code not people>
```
