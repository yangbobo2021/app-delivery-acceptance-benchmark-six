# Benchmark protocol

## Scope

These six applications test portability of an acceptance workflow across CLI, API, browser, desktop, batch, and terminal interfaces. They are intentionally small. A successful run here supports a claim about this fixed benchmark, not a claim that arbitrary production systems will pass or that every unexecuted scenario is correct.

Each project's `docs/requirements.md` is the product behavior contract. Use the project's README for build and launch instructions. Tests must exercise the actual user-facing process: command, HTTP request, browser, Electron window, or terminal. A unit call alone is not proof of delivery behavior.

For graphical and terminal interfaces, information and controls needed to complete or verify a requirement must remain readable and operable in the project's stated normal environment. Text must not disappear into its background, and required controls or status must not be covered. Visual taste, color palette, and decorative layout are not graded. Record the viewport or terminal dimensions and direct visual evidence when making a visual judgment. This shared rule applies to all applicable UI projects; it does not identify any particular defect.

## Version boundaries

`main` contains the current baseline. A test-result branch must record its exact baseline commit and must not alter product source while producing an acceptance result. Existing branches based on older commits retain their original meaning. Comparing results across branches requires checking both the baseline and the acceptance-workflow revision; neither may be assumed equal from branch names alone.

Keep the evaluator's defect manifest outside the baseline checkout and outside the input supplied to scenario and case agents. The manifest is pinned to a baseline commit and supplies the trigger, expected behavior, actual seeded behavior, and source provenance for each known defect. An evaluator may release it after a blind run. Unexpected failures must be checked against the requirements: confirmed additional product bugs become a repaired future baseline; false reports count as false positives. A selected scenario that never exercises a known trigger cannot count as a detected defect.

Preserve the first attempt, corrections, independent judgment, same-run coverage evidence, and archive/view checks. Report executed scenario counts and unexecuted counts separately. A branch that tests only selected scenarios must not claim full product acceptance.
