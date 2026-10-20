# 浏览器运行环境

适用：基线 be952659，macOS arm64；新验收需独立重建并验证，不继承旧验收的安装或 smoke 结果。实际版本和路径以当次 runtime manifest 为准。

项目位于仓库的 `projects/ts-web`。依赖清单为该目录 `package.json` 与 `package-lock.json`；执行 `npm ci --include=dev`、`npm run build`。项目服务入口是 `server.mjs`（`npm start`），`PORT=0` 可分配本地端口。已验证 Node 25.5.0、npm 11.8.0、esbuild 0.28.2。

浏览器测试可在本次验收的忽略运行目录局部安装 Playwright 1.56.1 及匹配的 Chromium，并设置同一 `PLAYWRIGHT_BROWSERS_PATH`。Node 内置 `node --test` 可作正式测试入口。非业务 smoke 应从真实 `server.mjs` 启动回环服务，启动 Chromium、载入首页和 `app.js`，确认资源可达后关闭浏览器及服务；本次已用 1280×800 视口完成此检查。它只证明运行链路，不证明待办业务。

所有安装缓存、浏览器二进制、构建产物和 smoke 输出留在当前验收的忽略目录或项目忽略的 `node_modules`、`dist`；测试应使用独立浏览器 context，关闭服务与进程。新机器重新解析 Node/npm 路径，按锁文件安装项目依赖，局部安装与平台匹配的浏览器，并重跑当次 smoke。Playwright 安装需要网络；Linux 可能需要浏览器系统依赖。
