# Invoice CLI coverage preparation

The checked baseline has no existing test tree, dependency manifest, coverage adapter,
or build step. The sole product process is Python's module entry `-m invoice`.
The empty `invoice/__init__.py` has no executable statements. Both `__main__.py`
and `totals.py` are explicit reporting inputs: source discovery alone must not
silently omit a module or its uncalled optional utility.

## Tool and reconstruction

Use the acceptance runtime's verified Python executable. Bootstrap pip with
`python -m ensurepip` in that acceptance's isolated venv, then
`python -m pip install -r projects/python-cli/tests/coverage_support/coverage-requirements.txt`.
This preparation installed and imported coverage.py 7.16.2 under Python 3.14.2.
The public API version and installed Python/extension/startup files are checked
against tool-lock.json on every live operation. Recreate the lock and preparation
when the interpreter, package, source, scope, or adapter changes; never reuse
another acceptance's installation or probe receipts.

Official references:
- https://coverage.readthedocs.io/en/7.16.2/api_coverage.html
- https://coverage.readthedocs.io/en/7.16.2/api_coveragedata.html
- https://coverage.readthedocs.io/en/7.16.2/subprocess.html
- https://coverage.readthedocs.io/en/7.16.2/commands/cmd_json.html

## Probes and independent reading

`collect.py zero|nonzero RAW inprocess|subprocess` starts/stops/saves the real
coverage.py collector. Zero mode runs no product code. Nonzero imports
`invoice.__main__` (which imports totals) without invoking main, calculate, or
any product function. The subprocess route uses the verified interpreter with
`-B -E`, exercising the project's environment-ignoring Python invocation.
Coverage's subprocess patch and parallel native databases handle child processes.
Only the host runs these complete probe routes.

`adapter.py probe-read RAW` reads each immutable native CoverageData database,
merges with CoverageData.update, and asks Coverage.json_report for explicit
source-file summaries. `direct.py RAW` independently copies databases to a
throwaway directory and invokes official `coverage combine` and `coverage json`.
It never imports the adapter. Both map native summary fields directly; neither
recognizes executable units, counts source lines, nor computes percentages.
No derived file is written to RAW by either reader.

The previous attempt's two zero readers failed with KeyError covered_branches,
while both nonzero routes passed. coverage.py 7.16.2 CoverageData.update selects
branch mode only when an input arc table contains actual arcs; all-empty arc
tables lost that mode during API and CLI merges. The new config includes the
coverage harness directory as a collection source, so real supervisor activity
preserves branch metadata, even when no product code executes. Explicit product
report inputs exclude all harness files and hits. No native counts are inserted
or modified by this workaround. Host probes must independently confirm it.
Readers create temporary derived reports beside RAW, never inside it. Percentages
are copied from the native percent_statements_covered/percent_branches_covered
fields rather than calculated or inferred from mixed coverage percentages.

The lightweight `adapter.py selfcheck EVIDENCE.json` checks the real adapter's
status propagation for unstarted collection, missing snapshots, and unsuccessful
finalization. Inputs and outputs are retained. Each host zero collector repeats
this status-only check into RAW/failure-paths.json, so the evidence is frozen with
its probe. This check does not execute business code or manufacture native counts.

## Operations and boundaries

The entry implements verify-preparation, run, finish, verify-report, summarize.
It reads spec.runtime_manifest and spec.probe_report, verifies their frozen bytes,
and does not rely on old private preparation fields. run supervises the original
argv through coverage.py's subprocess support and preserves its ordinary exit
code. finish requires actual native snapshots and completion state. A missing
child snapshot, failed start, or incomplete finalization yields unavailable
metrics and an incomplete report, or a hard verification error for missing or
changed evidence. A zero baseline can never substitute for missing execution.
verify-report recomputes from bound native databases; summarize merges through
CoverageData.update. This baseline has no commit diff, so changed_files and
changed_lines explicitly remain unavailable instead of reusing project numbers.

Only Python processes using this runtime and normal site initialization are
supported. `-S`, replacement interpreters, coverage-disabling environment edits,
remote processes, and detached/background children are outside the verified
routes. Abruptly killed collectors are incomplete. Parent and direct-child
snapshot checks do not certify arbitrary uninstrumented grandchildren: add a
new lifecycle/probe route before using such execution patterns. No business
acceptance case or business coverage has been produced by preparation. Host
probe approval and a later genuine run/finish/verify-report/summarize chain are
required before asserting that project coverage goals are achieved.
