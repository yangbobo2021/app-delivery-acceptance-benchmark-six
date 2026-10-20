# Preserved first-attempt and retest receipts

`MANIFEST.json` lists each file's original checkout, original relative path,
copy path, SHA-256 and byte count. The sources were copied byte-for-byte from
local test runs; the full archival records remain under each project's
`.acceptance` directory. These selected receipts explain process corrections
without putting temporary runtime environments on the public result branch.

- `setup/`: a shared-checkout foreign-change gate fired when parallel projects
  wrote acceptance files in one checkout. Execution continued in separate
  checkouts.
- `python/`, `go/`, `web/`, `electron/`, `java/`, `rust/`: coverage probes,
  first failed attempts, or final offline-view proofs for each project.
- `electron/first-note01-scenes.json` and `rust/first-tui04-scenes.json`:
  original scenario drafts. Matching revised files show targeted corrections
  made before case execution.
- `electron/first-cdp-debug-host.log`: first normal-case test-code failure on
  an unsupported diagnostic call, later repaired and re-executed.
- `java/relative-registry-request.json` and
  `java/first-blocked-case-retirement.json`: cross-directory coverage binding
  failure and its disposition. The generic path fix lives in a separate local
  Skill commit and did not alter the frozen benchmark revision.
- `rust/first-review.json`, `second-review.json`, `third-review.json` and
  `repaired-coverage-handoff.json`: review/repair trail before the final
  native LLVM and UI evidence were captured together.

These receipts document what happened; a failed setup or test-code attempt
does not count as a product finding.
