# Delivery acceptance benchmark

This repository contains six small, independently runnable applications for checking whether a delivery-acceptance workflow works across interfaces and runtimes. They are deliberately compact **synthetic benchmarks**, not representative production systems. Each project has six written requirements in its own `docs/requirements.md`; those requirements and the shared interface rule in [docs/benchmark-protocol.md](docs/benchmark-protocol.md) define what to test. Product source is not a source of additional requirements.

| Directory | Runtime and interface | Main user operation | Observable result |
| --- | --- | --- | --- |
| [projects/python-cli](projects/python-cli/README.md) | Python 3.10+, CLI | Summarize a CSV of invoice amounts | Exit status, JSON/stdout, stderr, input file |
| [projects/go-api](projects/go-api/README.md) | Go 1.23+, HTTP API | Reserve finite stock | HTTP status/body and durable state |
| [projects/ts-web](projects/ts-web/README.md) | TypeScript, browser | Manage and filter to-do items | Real browser UI and localStorage |
| [projects/electron-desktop](projects/electron-desktop/README.md) | TypeScript, Electron | Manage local notes | Real desktop UI, IPC, and user-data files |
| [projects/java-batch](projects/java-batch/README.md) | JDK 17+, batch CLI | Convert event CSV into account totals | Exit status, output CSV, stderr, input file |
| [projects/rust-tui](projects/rust-tui/README.md) | Rust 1.85+, terminal UI | Navigate and toggle a checklist | Real terminal display, input, and state file |

`main` is the baseline under test: project source, requirements, and public test rules only. Create an acceptance-result branch **from a specific `main` commit** and record that commit hash with the result. Generated scenarios, execution evidence, coverage, and result views belong on result branches or in ignored local execution directories. Earlier result branches remain historical records of the baseline they actually tested; they are not silently rebased when `main` advances.

In particular, `codex/acceptance-benchmark-round-1` and `codex/java-rust-acceptance-r6-20261020` were created before this unified six-project/UI baseline. Their evidence remains valid for the source revision recorded in each report, but neither branch is a test result for the current `main`.

The evaluator's itemized defect truth is kept separately from `main` so a scenario-generating agent cannot learn expected failures from the checkout. See [docs/benchmark-protocol.md](docs/benchmark-protocol.md) for scope, evidence, and scoring boundaries.
