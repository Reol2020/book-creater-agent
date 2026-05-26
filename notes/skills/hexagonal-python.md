# Hexagonal Python · 用包路径 + Protocol 模拟六边形

## 问题

Python 没有 Java 那样的编译期 module-path 隔离,反向 import(domain → adapter)
不会报错。但六边形(Ports & Adapters)这套要保证:
- domain / ports 不依赖 fastapi / sqlalchemy / chromadb / openai / anthropic
- 换数据库 / 换 LLM provider,业务代码零改动

## 套路

### 1. 包路径就是约束

```
backend/app/
├── domain/             # 纯 dataclass + 业务规则,零外部依赖
├── ports/              # Protocol 接口,domain 看得见
├── application/        # 用例服务,只 import domain + ports
├── adapters/
│   ├── inbound/api/    # FastAPI router → application
│   └── outbound/
│       ├── persistence/sqlite/    # 实现 ports/repository
│       ├── llm/direct/            # 实现 ports/llm_provider
│       └── knowledge/             # 实现 ports/chapter_retriever
└── config/
    └── container.py    # 唯一 DI 装配点
```

依赖方向:`adapters → application → ports → domain`,反过来禁止。

### 2. Protocol 而不是 ABC

```python
# ports/llm_provider.py
from typing import Protocol, AsyncIterator

class LlmProvider(Protocol):
    async def chat_stream(self, messages, system, ...) -> AsyncIterator[str]: ...
    async def chat_with_tools(self, messages, tools, system, ...): ...
```

Protocol 是结构化类型,adapter 不需要 `class XxxProvider(LlmProvider)`,
只要方法签名匹配就行。**测试时 mock 起来无成本**:写一个有同名方法的类即可。

### 3. Container 是唯一组装现场

```python
# config/container.py
class Container:
    def __init__(self, settings):
        engine = create_async_engine(settings.db_url)
        self.project_service = ProjectService(repo=SqliteProjectRepo(engine))
        self.agent_service = AgentService(
            llm=DirectLlmProvider(settings.llm),
            skills=build_default_registry(self.project_service, ...),
            context_builder=ProjectContextBuilder(
                retriever=SqliteFtsChapterRetriever(engine),
            ),
        )
```

`main.py` 只 `from app.config.container import build_container`。
adapter 永不被 main.py 直接 import。

### 4. 装饰器型 adapter

需要让 ProjectService 的 chapter 写入自动触发 RAG 索引?
**不要在 ProjectService 里加 retriever 依赖**,装饰器套一层:

```python
class _ChapterIndexingProjectService:
    def __init__(self, inner: ProjectService, retriever: ChapterRetriever):
        self._inner = inner; self._retriever = retriever
    async def update_chapter(self, ...):
        result = await self._inner.update_chapter(...)
        await self._retriever.index_chapter(result)
        return result
    def __getattr__(self, name): return getattr(self._inner, name)
```

## 反例

- ❌ 在 `domain/models.py` 用 SQLAlchemy `DeclarativeBase`:
  domain 直接绑死 ORM,以后想出嵌入式 / JSON 文件版本零希望。
  → domain 用 `@dataclass`;persistence 写自己的 ORM 表,二者用 mapper 互转。
- ❌ application 层直接 `from anthropic import Anthropic`:
  换 provider 改业务文件。→ 套 `LlmProvider` Protocol。
- ❌ adapter 之间互相 import:`outbound/llm` import `outbound/persistence` 拿历史。
  → 通过 application 编排,adapter 之间应平行无关系。
- ❌ 用 `Tuple[Repo, LLM, Retriever]` 当 service 入参:
  参数膨胀。→ 单参数 dataclass,或一个个 named arg。

## 工具兜底

Python 没有编译期约束,推荐:
- [import-linter](https://import-linter.readthedocs.io/) — 写规则禁止反向 import,CI 跑
- 代码 review 必检:`grep -r "from anthropic" backend/app/domain/` 必须为空

## 真实位置

- ports: `backend/app/ports/`
- adapters: `backend/app/adapters/outbound/`
- DI 装配: `backend/app/config/container.py`
- 装饰器型 adapter 实例: `_ChapterIndexingProjectService` in container.py
