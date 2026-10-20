# v1 run 1 pre-registered sample

This plan was fixed before inspecting the new run's generated scenario catalogs or executing business cases. It is evaluator-side material; do not copy it into the acceptance branch or provide it to scenario authors.

- Baseline: `be952659c7d93018e26793daf2e58fa8321601f4` (`baseline/2026-10-20-v1`).
- Run branch: `codex/run-v1-20261020-r1`.
- Skill revision: `c6ef9511347d07b4ff2aaf254754157b09b3f2a4`.
- Sample: 8 defect probes plus 6 expected-pass controls, 14 cases total. Selection uses only generated catalogs and requirement references, before seeing execution outcomes.

| Project | Defect probes to select | Expected-pass control to select |
| --- | --- | --- |
| Python CLI | INV-02: one account's exact total exceeds 32-bit signed range | Ordinary small valid CSV summation and JSON output |
| Go API | STOCK-03/STOCK-06: retry successful reservation after process restart | Ordinary fresh reservation and stock/status response |
| TS Web | TODO-04: global remaining count while a filter is active; TODO-02: completed item title readability | Add an ordinary task and see it in the list |
| Electron | NOTE-01: delete one of two same-title notes by identity; NOTE-01: readability when two notes exist | Create, edit, save and reopen one ordinary note |
| Java batch | BATCH-02: deduplicate a repeated event separated by another event | Ordinary valid input with two accounts and sorted CSV output |
| Rust TUI | TUI-02: selected-row readability with at least two items | Real-terminal one-item toggle, save and normal exit |

All probes must run through formal v4 cases, independent review, coverage where declared, and archive/offline viewing. If a catalog lacks a target, record a scenario-design miss before any code or result inspection. Do not synthesize or relabel a scene merely to make the sample pass. Any non-seeded product finding requires manual confirmation; a confirmed defect is repaired as the next product baseline rather than being counted as a Skill false positive.

## Frozen IDs after scenario review, before case execution

| Project | Defect probe IDs | Expected-pass control ID |
| --- | --- | --- |
| Python CLI | `INV-02-S02` | `INV-03-S01` |
| Go API | `STOCK-06-S02` | `STOCK-02-S01` |
| TS Web | `TODO-04-S02`, `TODO-02-S01` | `TODO-01-S01` |
| Electron | `NOTE-01-S06`, `NOTE-01-S07` | `NOTE-03-S01` |
| Java batch | `BATCH-02-S02` | `BATCH-03-S01` |
| Rust TUI | `TUI-02-S01` | `TUI-04-S01` |

All IDs are frozen before case execution. Execute one expected-pass control per project through archive and offline view before the defect probes. The Electron list was revised after an explicit human scenario-quality finding: the first NOTE-01/NOTE-03 drafts lacked a standalone one-note normal path. Rust TUI-04 likewise required a human-requested split of the ordinary single-item toggle from multi-item preservation. Preserve first and revised drafts; count these as human-assisted corrections, not one-pass Skill successes.
