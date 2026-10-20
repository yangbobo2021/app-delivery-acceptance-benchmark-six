# Java 批处理运行环境

项目要求 JDK 17+，没有第三方依赖清单。测试目录是 `projects/java-batch/tests`；项目入口见 `projects/java-batch/README.md`。

在本次验收专用运行目录建立 classes 目录，用同一 JDK 的 `javac --release 17 -encoding UTF-8 -d <classes> projects/java-batch/src/main/java/benchmark/BatchReport.java` 编译。后续测试通过同一 JDK 的 `java -cp <classes> benchmark.BatchReport` 启动；测试自身提供绝对输入和输出路径。运行环境 smoke 可仅验证 JVM 加载入口，无参数时预期程序给出用法并退出 2；这只证明入口可用，不是业务验收。

新机器先安装或解压 JDK 17+ 并核验 `java`、`javac` 版本，重建 classes 目录，重新编译和执行 smoke。隔离运行目录与编译产物不能跨验收复用。来源 AT-20261020-v1-java，冻结版本 be952659；本次 Agent 准备及宿主复验通过。覆盖率工具需在独立阶段另行准备。
