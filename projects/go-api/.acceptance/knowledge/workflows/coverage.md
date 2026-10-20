# Go API 覆盖率准备

本项目是通过独立 HTTP 进程运行的 Go 服务。当前测试目录的覆盖率适配器逐字节复制冻结的 `main.go` 与 `go.mod` 到本次验收隔离目录，并加入测试生命周期夹具；随后由 Go 原生工具以 `go test -c -trimpath -cover -covermode=atomic -coverpkg=stock.local/app` 构建可运行的服务二进制。夹具在 `_test.go` 中，产品统计由 Go 工具自身生成；服务正常结束后保留 `covmeta`、`covcounters` 原生数据和完成标记。

适配器使用 `go tool covdata debugdump`、`percent` 和 `merge` 读取、合并与统计原生数据，独立读取器对同一份只读数据核对。AT-20261020-v1-go 在基线 be95265 上的零/非零命中探针和最终准备入口验证通过。当前工具链只提供经验证的原生语句覆盖率；行与分支覆盖率须标记 unavailable，不能从语句百分比换算。

新机器须重新验证 Go 版本与构建、采集、收尾路径，重建本次验收专属运行环境和原生工具探针。后续正式用例必须通过已冻结的适配器启动服务；未启动、缺少原生计数或收尾不完整只能报告 incomplete/unavailable，不能把零命中基线当作业务采集。真实用例的 `run → finish → verify-report → summarize` 仍须逐次验证；准备探针不形成业务结论。工具的输出格式可能随 Go 版本变化，升级时重新核对适配器。
