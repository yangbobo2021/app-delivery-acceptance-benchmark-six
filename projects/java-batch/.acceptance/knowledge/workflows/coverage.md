# Java 覆盖率准备

当前 Java CLI 使用 JaCoCo agent 采集原生 exec，并由同版 JaCoCo CLI 的 `execinfo`、`report`、`merge` 给出源码文件的行与分支计数。项目测试树中的 `coverage_adapter.py`、`coverage_probe.py`、`coverage_direct.py`、`CoverageProbe.java` 和工具配置组成适配层；每次验收须重建并验证本次运行时、工具字节、源码和探针。工具调用参见 [JaCoCo agent](https://www.jacoco.org/jacoco/trunk/doc/agent.html) 与 [CLI](https://www.jacoco.org/jacoco/trunk/doc/cli.html)。

直接 JVM 和由 Python 测试入口启动的子 JVM 均要验证环境变量传递。零命中探针启动真实 JVM 会话但不加载目标类，定向命中只初始化目标类；两者都必须从同一份只读原生数据分别由适配器和 JaCoCo CLI 得出相同计数。没有原生快照、快照为空或收尾失败时标明缺口，不能记作实测零命中。

本次首次探针错误地认为 `dumponexit=false` 一定不创建文件；实际留下零字节文件，四条 collect 因断言中止。复测改为按文件大小与原生数据有效性判断，四组零/非零探针、独立直接读取和宿主准备验证均通过；首次失败和复测分别留在 AT-20261020-v1-java 的 coverage-1、coverage-2。来源版本 be952659，JaCoCo 0.8.12.202403310830。上述结果只证明采集能力；业务用例的同次采集仍需单独执行与复审。
