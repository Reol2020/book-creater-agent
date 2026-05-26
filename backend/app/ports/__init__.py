"""Port 接口层 —— Protocol 定义,业务层依赖的契约。

铁律:
  - 只 import app.domain + 标准库
  - 不 import 任何具体框架 / SDK
  - 不 import app.adapters / app.application / app.config

每个 Port 对应一类外部系统(持久化、向量库、LLM、文件系统、用户确认通道)。
"""
