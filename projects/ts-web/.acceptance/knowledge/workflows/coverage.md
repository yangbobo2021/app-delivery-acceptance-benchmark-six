# 项目覆盖率适配

适用：基线 be952659，项目源码位于 `projects/ts-web`。项目测试适配器放在可跟踪的 `tests/coverage-tools`；仓库的 `**/coverage/` 忽略规则会忽略名为 `coverage` 的目录。新验收应重新建立自己的运行环境、安装此测试目录锁定的工具依赖并实测探针，不继承本次结果。

已验证工具：Istanbul `istanbul-lib-instrument` 6.0.3 生成原始 JS/TS AST 的计数单位，`istanbul-lib-coverage` 3.2.2 负责原生快照合并和行/分支统计；Babel 7.29.7 处理注册函数 AST，esbuild 0.28.2 在插桩后移除 TypeScript 类型；Node 25.5.0 与 Playwright 1.56.1/Chromium 负责进程和浏览器生命周期。工具路径与版本需以当次准备记录实测为准。

Node 服务、Chromium 页面和构建入口分别用非业务零命中和非零命中探针验证，适配器与专用工具只读同一原生数据并返回一致指标。浏览器零探针最初因把多语句注册脚本交给 `page.evaluate` 且 CSP 下动态全局获取不兼容而失败；修复后在隔离空白页面用 Playwright `addScriptTag` 执行注册脚本，并将 Istanbul 全局对象配置为 `globalThis`、关闭动态函数获取。首次失败仍保存在该验收的旧尝试。

正式用例须使用已准备 catalog 绑定的入口，实际运行期间保存原生快照并可靠收尾；缺少快照报 `unavailable`，收尾不完整报 `incomplete`，不能用零探针代替业务计数。项目基线没有 PR 修改文件/修改行范围，相关两项统计应为不可用。浏览器测试使用独立 context、正常桌面视口并保存关键状态截图。新电脑需先按运行环境入口重建项目服务和 Chromium，再按测试目录锁文件安装覆盖率工具并重新验证全部路由。
