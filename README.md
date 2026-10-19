# Delivery acceptance benchmark

Six small applications provide a repeatable, multi-runtime target for evaluating a delivery-acceptance workflow. Each application has its own original requirements in `docs/requirements.md` and can be run independently.

| Directory | Application |
| --- | --- |
| `projects/python-cli` | Python invoice-summary CLI |
| `projects/go-api` | Go inventory HTTP service |
| `projects/ts-web` | TypeScript browser to-do app |
| `projects/electron-desktop` | TypeScript Electron notes app |
| `projects/java-batch` | Java daily receipt batch processor |
| `projects/rust-tui` | Rust interactive terminal checklist |

Each baseline commit freezes the source set for its acceptance round. Acceptance runs, generated scenarios, coverage data and results belong on separate test branches or in ignored local execution directories. The application requirements are the behavioral authority; implementation details are not additional requirements.
