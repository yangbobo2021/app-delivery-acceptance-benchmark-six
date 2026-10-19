# Terminal checklist

Requires Rust 1.85+ and a real color-capable terminal (`TERM=xterm-256color`, with `NO_COLOR` unset). Build with `cargo build --locked`; run `cargo run --locked -- --state /absolute/checklist.txt`. The state file has `id|title|done` lines (`done` is `0` or `1`), and must exist before launch. Press `j`/Down or `k`/Up to select a row, Space to toggle it, and `q` to quit. See `docs/requirements.md` for acceptance rules.

