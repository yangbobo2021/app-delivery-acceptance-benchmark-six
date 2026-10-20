# Rust 终端清单覆盖率准备

本项目用 `rustc -C instrument-coverage` 生成原生 profile 和映射，使用同一 Rust 工具链对应的 `llvm-profdata merge` 与 `llvm-cov export --summary-only` 采集、合并并统计行覆盖率。官方依据为 Rust `instrument-coverage`、LLVM `llvm-profdata` 与 `llvm-cov` 文档。适配器位于 `projects/rust-tui/tests/llvm_coverage/`，只负责启动、格式与路径绑定，统计分母和命中数由 LLVM 提供。此稳定版工具链没有可用的分支映射，分支指标须标为 unavailable。

先核验本验收的 runtime manifest、源码哈希、当前目标平台及锁定 Cargo 依赖。以工具链发布清单提供的 URL 和 SHA256 安装匹配的 LLVM 工具到当前验收独立目录，再核验工具版本。实际场景使用新的插桩 `CARGO_TARGET_DIR`，继承 `RUSTFLAGS`、`LLVM_PROFILE_FILE` 和 `TERM=xterm-256color`，不设置 `NO_COLOR`，等所有产品进程结束后执行 run → finish → verify-report → summarize。不得将覆盖率零探针的 profile 代替真实场景的缺失快照；采集未启动、快照缺失、收尾中断应保持 incomplete/unavailable。

AT-20261020-v1-rust 在 be952659 上的覆盖率 Agent 使用已验证 runtime-4，零与非零命中探针均通过，适配器和独立 LLVM reader 对同一原生数据统计一致；宿主再次运行 `coverage_preparation.py verify` 成功。探针仅验证工具链能力，不是业务用例。首次整体下载较慢，Agent 停止并保留部分文件和停止收据，之后分段下载并核验成功；新环境须按本机工具链重建和复验。测试助手目录使用 `llvm_coverage`，避开项目对 `coverage/` 的忽略规则。冻结 inventory 为 requirements-baseline，因此 changed-file/changed-line 范围不可用。
