Coverage uses rustc -C instrument-coverage, llvm-profdata merge, and llvm-cov export
--summary-only. Units, zero counts, merge and percentages come from LLVM. Stable
Rust does not emit branch mappings here; branch coverage is unavailable.

Official references:
https://doc.rust-lang.org/rustc/instrument-coverage.html
https://llvm.org/docs/CommandGuide/llvm-profdata.html
https://llvm.org/docs/CommandGuide/llvm-cov.html

The isolated probe includes the unchanged source as a module; its zero route
never invokes any product function, while touch only invokes argument parsing.
Both retain unused coverage mappings with link-dead-code. These are tool probes,
not business tests. The host runs both readers on the same immutable native
binary and profraw; readers merge into temporary directories outside raw.

Real executions use a fresh instrumented Cargo target directory. Business test
commands must inherit CARGO_TARGET_DIR, RUSTFLAGS and LLVM_PROFILE_FILE, use cargo
run or CARGO_TARGET_DIR/debug/terminal-checklist, and wait for all product child
processes to exit normally. Explicitly launching a cached noninstrumented binary
is not supported and must result in missing native coverage, never zero percent.
Missing snapshots and interrupted lifecycle are unavailable/incomplete. A valid
zero probe profile is never used as a fallback for a real execution.

Preparation verification consumes the protocol's spec.runtime_manifest and
spec.probe_report (and their hashes), not historical private probe fields.
On a measured finish, native/llvm-native-archive retains the merged profdata,
full LLVM export, summary export and processing record in raw_evidence. Report
verification recomputes metrics from the bound binary and original profraw;
archived exports supplement those inputs and never replace missing snapshots.
The host must run fresh zero/nonzero probes and verify-preparation after freezing
these adapter files, then validate the actual scene lifecycle separately.
