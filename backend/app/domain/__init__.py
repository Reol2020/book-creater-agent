"""纯业务层。

铁律(import-linter 强制):
  - 不允许 import 任何外部框架(fastapi / sqlalchemy / chromadb / anthropic / openai)
  - 不允许 import app.adapters / app.application / app.config
  - 只允许 import 标准库 + dataclasses + 自己

一切持久化、网络、UI 关心的事情都通过 ports 间接完成,domain 只描述
"业务对象长什么样、业务规则是什么"。
"""
