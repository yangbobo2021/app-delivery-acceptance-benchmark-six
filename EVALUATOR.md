# Human evaluator truth: six-project baseline v1

This public evaluator branch starts from the baseline tag and therefore contains the exact same six projects and requirements, plus this truth file. The file is absent from `main` and ordinary test branches. Do **not** give it to scenario-generating or case-executing agents before a blind run. Because this branch is public, an agent that searches remote branches can still find it; strict blindness requires withholding the truth outside the public repository.

- Baseline repository: `yangbobo2021/app-delivery-acceptance-benchmark-six`
- Baseline branch: `main`
- Baseline tag: `baseline/2026-10-20-v1`
- Exact baseline commit: `be952659c7d93018e26793daf2e58fa8321601f4`
- Known seeded defects: 8 distinct defects across 6 projects. Two projects each contain an additional UI defect.
- This list is the known-defect oracle, **not** a claim that all other project behavior has been proven correct. An unexpected report requires independent requirements-based adjudication.

The first four projects' functional defects were already present in the original four-project source commit `c08f2c1`; Java and Rust arrived with one defect each in the six-project addition `cd1ecc6`. These six have no separate healthy pre-injection commit, so their seeded provenance is documented but not demonstrated by an isolated mutation diff. The two UI defects have an isolated two-line injection commit `292214b`, following layout commits `0c67d65` and `8fd020a`. The current Web and Electron HTML blobs exactly match the previously tested UI-defect branch's `aea826e` blobs.

## Known-defect oracle

| ID | Project; requirement or public rule | Minimal trigger and correct result | Seeded result and source |
| --- | --- | --- | --- |
| PY-EXACT-SUM | Python CLI; `INV-02` | CSV header `account,amount_cents` and three `A,1000000000` rows; `totals.A` must be `3000000000`, `row_count` 3 | `totals.A=-1294967296`; explicit 32-bit wrap in `invoice/totals.py:1-3` |
| GO-RETRY-RESTART | Go API; `STOCK-03`, `STOCK-06` | Reserve `request_id=r1, quantity=2`, close normally, restart with same state directory, retry: HTTP 200 with original `available=8`; stock remains 8 | Retry returns HTTP 201 with `available=6`; loaded `Requests` is cleared in `main.go:42` |
| WEB-REMAINING | TS Web; `TODO-04` | Add A and B, mark B complete, select Completed filter: the global unfinished count must still be 1 | Counter becomes 0 because `src/app.ts:10` counts only visible rows |
| WEB-COMPLETED-TEXT | TS Web; public interface rule and `TODO-02` | At normal desktop viewport, mark a task complete: its title remains readable while the checked state is visible | Completed title is near-white on a light surface; injected rule in `src/index.html` (`#tasks li:has(input:checked) span`, `color: #f8f9fc`) |
| NOTE-SAME-TITLE | Electron; `NOTE-01` | Create two notes with the same title and distinct IDs; delete one ID: the other remains with its original body | Both disappear because `src/store.ts:16` filters by title instead of ID |
| NOTE-TINY-LIST | Electron; public interface rule and `NOTE-01` | With two notes in the normal window, both list titles remain readable and selectable | Both list titles shrink to `6px`; injected `#notes:has(button + button) button` rule in `src/index.html` |
| JAVA-DUP-EVENT | Java batch; `BATCH-02` | Rows `e1,A,100`, `e2,A,100`, `e1,A,100`: output A total 200 and count 2 | Output A total 300 and count 3; `BatchReport.java:80-86` records seen ID but still aggregates duplicate |
| RUST-SELECTED-TEXT | Rust TUI; `TUI-02` | In a real `TERM=xterm-256color` terminal at 80×24 with two valid items, selected row text is readable | Selected foreground and background are both `DarkGrey`; `src/main.rs:127-140` |

The Web and Electron visual findings are usability findings, not judgments of decorative taste. The original Web requirement explicitly left visual design unspecified; the shared rule in baseline `docs/benchmark-protocol.md` and the two projects' current requirement introductions now state the readability boundary **before future evaluations**. Earlier test-result branches retain their own earlier requirement versions. An external reviewer should consider this provenance when comparing historical scores.

## Evidence and confidence

- PY-EXACT-SUM, GO-RETRY-RESTART, and JAVA-DUP-EVENT were independently re-run on 2026-10-20 against the product source of `179bce9`, which is unchanged at baseline `be95265`; observed values above were reproduced. The Python entry and the Go, Java, Web, Electron, and Rust builds passed. Rust's installed Cargo was outside the default shell PATH. The Electron binary reported version 44.9.0 after its normal install.
- WEB-COMPLETED-TEXT and NOTE-TINY-LIST were visually exercised and independently reviewed in the historical `codex/ui-acceptance-r5-20261020` result branch. Byte-identical HTML blobs were checked against the new baseline. The current baseline has not undergone a new end-to-end UI run after the merge.
- JAVA-DUP-EVENT and RUST-SELECTED-TEXT were formally exercised and independently reviewed in `codex/java-rust-acceptance-r6-20261020`; Java/Rust product sources are unchanged in the new baseline.
- The four original projects' functional defects were exercised in earlier result branches. Source inspection in the current baseline independently ties each to the written contract. A fresh full six-project defect run has not been performed on this exact baseline.
- No project has yet passed exhaustive testing of all requirements. Do not score an unexpected failure as a false positive merely because it is absent from this oracle; verify and, if real, repair the product in a later baseline revision.

## Scoring boundary

For each selected scenario, record whether it actually reached the trigger. A known defect is a true positive only if the run reaches its trigger, reports the correct product failure, and the independent review accepts the evidence. If a selected trigger is reached but the defect is missed, count a false negative. A product-BUG report outside the oracle is adjudicated against requirements and actual behavior before being called an extra true positive or a false positive. Do not count unexecuted scenarios in a detection rate. A single planted defect seen in multiple scenarios remains one defect, even if multiple scenario results are BUG.
