# Rust 终端清单运行环境

项目入口和交互约定见 `projects/rust-tui/README.md`；依赖以 `Cargo.toml` 和 `Cargo.lock` 为准。使用 Rust 1.85+、Cargo、Python 3，以及与当前平台兼容的编译链接工具。验收终端使用 `TERM=xterm-256color`，不设置 `NO_COLOR`。

在每次验收独立目录设置 `CARGO_HOME` 和 `CARGO_TARGET_DIR`。先运行 `cargo fetch --locked --target <当前目标三元组>`，再在项目目录运行 `cargo build --locked --offline`；构建和后续测试使用同一工具链与目标目录。用 Python 标准库 PTY 创建 80×24 真实终端，放入临时最小有效状态文件，以 README 的 `cargo run --locked --offline -- --state <绝对路径>` 入口启动，收到启动输出后按 `q` 并检查正常退出。这个 smoke 只证明环境与终端入口可运行，不能当作业务场景结果。

首次准备使用无 `--target` 的 `cargo fetch --locked`，它下载多个平台的依赖，600 秒超时；失败日志保留在来源验收的 runtime-3。复测限定 `aarch64-apple-darwin` 目标，在全新本 ID 缓存中 fetch 约 200 秒、离线构建约 11 秒，PTY smoke 与宿主复验通过。新电脑应选择自己的目标三元组、重新下载锁定依赖并复验；不要沿用本机缓存或旧验收的通过凭证。来源 AT-20261020-v1-rust，冻结版本 be952659。覆盖率工具需在独立阶段另行准备。
