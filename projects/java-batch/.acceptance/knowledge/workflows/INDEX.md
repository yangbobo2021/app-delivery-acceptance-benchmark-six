# 工作流程

## 职责
记录本项目可重建的测试运行流程，不包含本机安装物或业务判据。

## 何时读取
准备 Java 运行环境或恢复本项目验收时读取。

## 内容入口
- [runtime.md](runtime.md)：JDK 环境、编译与轻量入口 smoke。适用于项目 `projects/java-batch` 的冻结 Java CLI；来源 AT-20261020-v1-java，已在 be952659 上由运行环境准备入口和宿主 `verify` 验证。业务判据仍以 `docs/requirements.md` 为准。
- [coverage.md](coverage.md)：JaCoCo 原生采集、零/非零探针与失败收尾处理。适用于当前 Java CLI；来源 AT-20261020-v1-java，已在 be952659 上通过专用覆盖率准备门禁与宿主复核。
