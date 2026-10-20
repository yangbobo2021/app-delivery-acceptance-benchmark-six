# 桌面应用覆盖率

适用基线 be952659。覆盖率工具位于项目 `tests/coverage-tools`，独立锁定依赖。每次新验收先独立验证 Node、npm、Electron 和 esbuild 环境，再按测试包锁文件安装依赖。

工具以 esbuild 转换 TypeScript、Istanbul 按源码插桩及映射源码行，在隔离应用副本中构建。主进程、隔离 preload 世界和 renderer 世界分别保存原生计数，再由 Istanbul 合并、映射并汇总。正式用例从测试目录的 `launch.cjs` 助手启动本轮插桩应用，使用独立用户数据目录，保留原有断言和退出码；启动原应用不会采集此路线的覆盖率。

新验收须由宿主重新执行各路由零命中及轻量非零命中探针、独立只读复算、缺失快照与收尾失败检查，并对最终 profile 执行 `verify-preparation`。正常导航应保存文档快照，关闭与退出前完成收尾。没有原生快照的来源不能用零基线填充；缺少快照或收尾不完整分别标为 unavailable 或 incomplete。

本轮 `main.ts`、`preload.ts`、`renderer.ts`、`store.ts` 已有可测路线。独立进程中的 `build.mjs` 无已验证采集路线，整份准备保持 partial。每次运行的具体 profile、原生报告和限制以该次验收的冻结记录为准。
