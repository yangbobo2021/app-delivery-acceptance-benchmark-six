# Python CLI 本地运行环境

项目位于仓库的 `projects/python-cli`，要求 Python 3.10+，仅使用标准库，没有依赖清单。从该目录用隔离虚拟环境中的解释器执行 `python -m invoice --input <绝对 CSV 路径>`；从别的工作目录调用时须把项目目录加入 `PYTHONPATH`。

用本机 Python 3.10+ 创建本次验收的虚拟环境，可使用 `python -I -m venv --without-pip <隔离运行目录>/venv`。smoke 从项目目录执行该虚拟环境解释器的 `-B -E -m invoice --help`，只验证解释器、模块导入和参数入口；不提供业务 CSV 或断言汇总行为。`-B` 避免写字节码，`-E` 忽略外部 Python 环境变量。

新机器先定位兼容解释器的绝对路径，再为本次验收新建虚拟环境并重新 smoke；不可复制旧验收的环境或通过凭据。此步骤来源于 AT-20261020-v1-python 的首次运行环境准备，在 be95265 上完成创建及 smoke。范围变更后须为新范围重新绑定并验证。
