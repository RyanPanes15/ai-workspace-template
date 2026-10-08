# parity module (optional)

For setups with a sibling workspace (tester, admin) that shares some files with this
one. `docs/parity.md` is the registry (four relationship types, tables the checker
parses); `parity_check.py` hashes byte-identical copies, compares the `check` regex on
mirrored copies, and lists files that exist in two workspaces but are not registered.
Run it when reviewing a PR that touches a paired file, or weekly. Exit 1 = drift.
