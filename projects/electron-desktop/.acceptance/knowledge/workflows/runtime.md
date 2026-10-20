# 桌面应用运行环境

适用：基线 be952659、macOS arm64 登录会话。新验收须独立安装并复验，不能沿用旧验收的路径或 smoke 通过记录。实际版本和路径以当次 runtime manifest 为准。

项目位于仓库的 `projects/electron-desktop`。依赖清单为该目录的 `package.json` 和 `package-lock.json`。已验证 Node 25.5.0、npm 11.8.0、Electron 44.9.0、esbuild 0.28.2。使用 `npm ci --include=dev` 安装，显式执行项目 `node_modules/electron/install.js` 取得桌面二进制，再执行 `npm run build`；依赖与 `dist` 均为项目忽略产物。

实际应用入口为项目目录的 Electron 可执行文件，以 `.` 和独立的 `--user-data-dir` 启动，等同 `npm start -- --user-data-dir ...`。非业务 smoke 通过动态调试端口连接实际渲染窗口，确认 `dist/index.html` 页面载入完成，然后终止本次进程组并清理隔离用户数据；此流程没有读取、保存或删除便签。本次宿主验证与重验均成功。后续业务场景须使用新鲜用户数据目录、实际 Electron 进程与窗口，并保存窗口上下文和截图。

安装缓存、临时用户数据、smoke 记录均留在当前验收忽略目录。新电脑重新解析 Node/npm 路径、按锁文件安装，并在可显示桌面应用的会话中复验。Electron 下载需要网络和平台匹配的二进制；原生模块及窗口能力由当次验证结果决定。
