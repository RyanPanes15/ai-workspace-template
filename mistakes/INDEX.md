# Mistake index — read this before non-trivial work

Open a file when its triggers match the task. Add a line here in the same change that
creates a file. Format: `file` · severity · triggers.

| file | sev | read when the task involves… |
| --- | --- | --- |
| [static-read-of-runtime-bug](static-read-of-runtime-bug.md) | high | enable/disable, blank-on-load, stale value, toggle, race, slow render, empty dropdown |
| [wrong-environment-evidence](wrong-environment-evidence.md) | high | missing rows, can't find the reporter's record, results differ from tester's |
| [invalid-negative-trial](invalid-negative-trial.md) | high | "not reproducible", "no error", verifying a fix in the browser |
| [name-keyed-sweep](name-keyed-sweep.md) | high | horizontal sweep / 横展開, "same bug elsewhere", sibling screens |
| [vacuous-tool-pass](vacuous-tool-pass.md) | medium | lint / tests / typecheck / CI results |
| [truncated-edit](truncated-edit.md) | medium | editing large files, post-edit check failure |
| [speculative-abstraction](speculative-abstraction.md) | medium | new projects/modules, "flexible", generic helpers, config options, base classes |
| [dropped-reference-rule](dropped-reference-rule.md) | high | porting/migrating a screen or module, parity with the old system |
| [whole-file-read](whole-file-read.md) | medium | large file, stack trace, reference screen, PR review, DDL |
