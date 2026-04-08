# Phase 18: Python 3.9 兼容与依赖修复 - Context

**Gathered:** 2026-04-08
**Status:** Ready for planning

<domain>
## Phase Boundary

将整个应用降级为 Python 3.9 兼容：类型注解降级（PEP 604 → Optional、PEP 585 → typing 泛型）、依赖版本锁定（numpy、Pillow）、SQLite 外键启用。不包含任何功能变更，纯基础设施/兼容性工作。

</domain>

<decisions>
## Implementation Decisions

### 类型注解降级范围
- **D-01:** 仅替换运行时求值位置的 `X | None` → `Optional[X]`，包括 SQLAlchemy `Mapped[X | None]`（19 个 model 文件，61 处）和 Pydantic `BaseModel` 字段定义（schemas 目录）
- **D-02:** 服务层、引擎、工具函数中的纯类型注解保留 `X | None` 不变 — `from __future__ import annotations` 已在所有文件中启用，纯注解不会被运行时求值
- **D-03:** 需要为替换目标文件添加 `from typing import Optional`（若尚未导入）

### PEP 585 内建泛型处理
- **D-04:** 与注解降级策略一致 — 仅替换运行时求值位置（Pydantic schemas、SQLAlchemy models）中的 `dict[str, X]` → `Dict[str, X]`、`list[X]` → `List[X]` 等
- **D-05:** 服务层/引擎中的纯注解保留 PEP 585 语法不变
- **D-06:** 需要为替换目标文件添加 `from typing import Dict, List, Tuple, Set`（按需）

### SQLite 外键启用
- **D-07:** 使用 SQLAlchemy 官方推荐的 event listener 方式：`event.listen(engine, 'connect', set_sqlite_pragma)`，在 `backend/app/core/database.py` 中添加
- **D-08:** 仅对 SQLite 连接启用，PostgreSQL 连接不受影响（通过检查 dialect 判断）

### 依赖版本锁定
- **D-09:** 仅降级 numpy（2.2.1 → 2.0.2）和 Pillow（11.0.0 → 10.4.0），其他依赖当前版本已兼容 Python 3.9
- **D-10:** 降级后需验证 pandas 批量导入和图片压缩/解析功能正常工作

### Claude's Discretion
- 具体的正则表达式或 AST 工具选择（用于批量替换类型注解）
- 测试验证的执行顺序和范围
- 是否需要添加 `eval_type_backport` 作为 Pydantic v2 在 3.9 上的支持依赖

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 类型系统
- `backend/app/core/database.py` — SQLAlchemy engine 配置、session 工厂、`init_database()`，SQLite FK 修改目标
- `backend/app/models/` — 全部 19 个 model 文件包含 `Mapped[X | None]`，类型降级主要目标
- `backend/app/schemas/` — Pydantic schema 文件包含 PEP 604 和 PEP 585 语法，运行时求值

### 依赖配置
- `requirements.txt` — numpy==2.2.1、Pillow==11.0.0 需降级

### 代码约定
- `.planning/codebase/CONVENTIONS.md` — 当前类型注解约定（PEP 604、PEP 585 用法说明）

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `from __future__ import annotations` 已在所有 backend 文件首行，保护纯注解位置的 PEP 604/585 语法

### Established Patterns
- Models 使用 mixin 继承：`class Employee(UUIDPrimaryKeyMixin, CreatedAtMixin, UpdatedAtMixin, Base)`
- Schemas 使用 `ConfigDict(from_attributes=True)` 进行 ORM 序列化
- `_engine_kwargs()` 已根据 `sqlite` vs 非 sqlite 区分配置 — 外键 event listener 可同样按此模式

### Integration Points
- `database.py` 中的 `create_db_engine()` 是添加 SQLite FK event listener 的位置
- `requirements.txt` 是依赖版本的唯一配置源

### 影响面统计
- `Mapped[X | None]`：19 个 model 文件，61 处
- `X | None`（schemas/services/engines）：30 个文件，164 处（仅 schemas 需要改）
- `dict[]/list[]/tuple[]/set[]`：30+ 文件，112 处（仅 schemas/models 需要改）

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 18-python-3-9*
*Context gathered: 2026-04-08*
