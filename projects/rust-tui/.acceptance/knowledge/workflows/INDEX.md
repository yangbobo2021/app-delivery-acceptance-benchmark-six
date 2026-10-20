# 工作流程

## 职责
记录本项目可重建的测试运行流程和已验证的环境故障处理，不包含本机安装物或业务判据。

## 何时读取
准备 Rust TUI 运行环境或恢复本项目验收时读取。

## 内容入口
- [runtime.md](runtime.md)：Rust/Cargo 锁定依赖、当前平台下载、PTY 入口 smoke。适用于 `projects/rust-tui`；来源 AT-20261020-v1-rust，已在 be952659 上由运行环境准备入口和宿主 `verify` 验证。
- [coverage.md](coverage.md)：Rust 原生 LLVM 覆盖率采集、配套工具安装与探针验证。适用于 `projects/rust-tui`；来源 AT-20261020-v1-rust，be952659，coverage-1。
