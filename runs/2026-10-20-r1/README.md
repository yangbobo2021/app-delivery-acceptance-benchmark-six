# Six-project acceptance benchmark: v1 run 1

This branch records a **sampled** delivery-acceptance run against baseline
[`be952659c7d93018e26793daf2e58fa8321601f4`](https://github.com/yangbobo2021/app-delivery-acceptance-benchmark-six/commit/be952659c7d93018e26793daf2e58fa8321601f4)
(`baseline/2026-10-20-v1`). The tested acceptance Skill was frozen at
`c6ef9511347d07b4ff2aaf254754157b09b3f2a4`. Product source is identical
to the baseline. [The sample and its scenario IDs](SELECTION.md) were selected
before business-case execution. The evaluator truth was read only after all
14 selected cases finished; the [public evaluator branch](https://github.com/yangbobo2021/app-delivery-acceptance-benchmark-six/blob/codex/oracle-20261020-v1/EVALUATOR.md)
is procedurally separate, but its public availability means this is **not a
strict blind evaluation**.

## Result

| Project | Generated scenes | Executed | Expected-pass control | Known defect probes | Cumulative coverage | Archive |
| --- | ---: | ---: | --- | --- | --- | --- |
| [Python CLI](../../projects/python-cli/.acceptance/AT-20261020-v1-python/) | 28 | 2 | `INV-03-S01` passed | `INV-02-S02` P1 found | measured: 34/44 lines, 7/14 branches | [record](../../projects/python-cli/.acceptance/AT-20261020-v1-python/records/evidence-02d248bbb9804884b790d5c56eb81dfb/) |
| [Go API](../../projects/go-api/.acceptance/AT-20261020-v1-go/) | 26 | 2 | `STOCK-02-S01` passed | `STOCK-06-S02` P0 found | measured: 48/70 statements; line/branch unavailable | [record](../../projects/go-api/.acceptance/AT-20261020-v1-go/records/evidence-5463dfe096c74b9a9492875b1169693d/) |
| [TS Web](../../projects/ts-web/.acceptance/AT-20261020-v1-web/) | 23 | 3 | `TODO-01-S01` passed | `TODO-04-S02` P1 and `TODO-02-S01` P0 found | measured; per-file details in record | [record](../../projects/ts-web/.acceptance/AT-20261020-v1-web/records/evidence-ca0c33a0a4c045079b0ef01a1fe6c0fb/) |
| [Electron](../../projects/electron-desktop/.acceptance/AT-20261020-v1-electron/) | 25 | 3 | `NOTE-03-S01` passed | `NOTE-01-S06` and `NOTE-01-S07` P0 found | **incomplete**: main, preload, renderer and store measured; `build.mjs` unsupported | [record](../../projects/electron-desktop/.acceptance/AT-20261020-v1-electron/records/evidence-ac0b2035af3641b98cfa26027287cf63/) |
| [Java batch](../../projects/java-batch/.acceptance/AT-20261020-v1-java/) | 31 | 2 | `BATCH-03-S01` passed | `BATCH-02-S02` P1 found | measured: 46/63 lines, 24/44 branches | [record](../../projects/java-batch/.acceptance/AT-20261020-v1-java/records/evidence-d6818dc1b77440669ed5f6e7a63081b5/) |
| [Rust TUI](../../projects/rust-tui/.acceptance/AT-20261020-v1-rust/) | 26 | 2 | `TUI-04-S01` passed | `TUI-02-S01` P0 found | measured: 100/128 lines; branch unavailable | [record](../../projects/rust-tui/.acceptance/AT-20261020-v1-rust/records/evidence-8782d77e4cb248a9ab55df2ec203f922/) |

**Totals:** 159 scenes generated, 14 executed, 145 unexecuted; 6/6 selected
expected-pass controls passed and 8/8 selected known defects were detected and
independently judged `product_bug`. There were no additional confirmed product
findings in this sample. Two UI defects were also incidentally visible in
neighboring Electron scenes; each is counted once. These are observed counts,
not estimates of accuracy on the 145 unexecuted scenes or on other projects.
Coverage units are native to each tool and are not comparable across languages.

The eight reproduced defects were: Python's 32-bit overflow on a legal invoice
sum; Go's duplicate reservation after a successful retry across restart; Web's
filter-dependent global remaining count and unreadable completed title;
Electron's deletion of both same-title notes and unreadably tiny two-note list;
Java's non-adjacent duplicate event counted twice; and Rust's selected-row text
disappearing against its background. The three visual findings were judged from
frozen real-interface screenshots at recorded display dimensions, not just
source inspection. Each archive retains the case, execution, independent
review, coverage output, and cumulative result.

## Process checks and corrections

Each project completed runtime preparation, coverage preparation, scenario
generation, one control case, defect cases, independent review, cumulative
archive and read-only result view. All six archives were checked in a checkout
without `.acceptance-local`; each read-only view recovered the selected case
IDs, verdicts, scene denominator and coverage disposition. The
[diagnostic manifest](diagnostics/MANIFEST.json) hashes preserved first-attempt
and retest receipts; [diagnostic notes](diagnostics/README.md) explain them.

The first Electron and Rust scene drafts lacked standalone ordinary paths and
were revised after human review, before case execution. This run therefore
does not establish that all six catalogs were good on the first generation.
The Java coverage handoff initially used relative paths, so case execution
from another working directory rejected an otherwise prepared adapter. A
generic absolute-path preflight was committed separately to the **un-pushed**
Skill worktree as `b4ee37f414ddde6040f5a813fdab6a3da60662d8`; this result
branch continues to report the frozen Skill revision above. Rust needed a
second coverage adapter and a fresh normal-case execution before the reviewer
received native LLVM export and UI evidence in the same run. The earlier
failed/repair judgments remain preserved.

Other first-attempt failures involved parallel workers sharing one checkout,
project-specific adapter probes, and Electron test code calling an unavailable
CDP diagnostic interface. Those were corrected or isolated without counting
them as product defects. Their receipts are retained. Electron's `build.mjs`
remains explicitly unsupported in cumulative coverage because no validated
same-run route covered that independent build process; measured app processes
are not mislabeled as whole-project completeness.

This small, intentionally synthetic suite supports the narrower observation
that this Skill revision completed six interface/language flows and identified
the eight selected known triggers while passing six selected controls. It does
not prove full acceptance of any project, absence of other bugs, or performance
on realistic large applications. Five known functional defects and one visual
defect came from the source projects; two further visual defects have isolated
injection commits. See
the evaluator manifest for exact provenance.
