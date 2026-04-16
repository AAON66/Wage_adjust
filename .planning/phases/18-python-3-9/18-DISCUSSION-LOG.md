# Phase 18: Python 3.9 兼容与依赖修复 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-08
**Phase:** 18-python-3-9
**Areas discussed:** 类型注解降级范围, SQLite 外键启用方式, 依赖兼容性审计范围, PEP 585 内建泛型处理

---

## 类型注解降级范围

| Option | Description | Selected |
|--------|-------------|----------|
| 仅运行时求值位置（推荐） | 只改 SQLAlchemy Mapped[] 和 Pydantic BaseModel 字段（运行时求值），服务层/工具函数的纯注解保留 X\|None（已有 from __future__ import annotations 保护） | ✓ |
| 全量替换所有文件 | 统一将所有 str\|None 替换为 Optional[str]，保持代码风格完全一致，但工作量更大 | |
| Claude 决定 | 由 Claude 根据实际情况判断哪些文件需要改 | |

**User's choice:** 仅运行时求值位置（推荐）
**Notes:** 利用 `from __future__ import annotations` 已有的保护，最小化改动范围

---

## SQLite 外键启用方式

| Option | Description | Selected |
|--------|-------------|----------|
| event listener（推荐） | SQLAlchemy 官方推荐方式：event.listen(engine, 'connect', set_sqlite_pragma)，在 database.py 中添加，每次连接自动执行 | ✓ |
| 连接层配置 | 通过修改 create_engine 的 connect_args 传入 PRAGMA，但 SQLite 的 PRAGMA 不支持这种方式 | |
| Claude 决定 | 由 Claude 选择最合适的实现方式 | |

**User's choice:** event listener（推荐）
**Notes:** 无

---

## 依赖兼容性审计范围

| Option | Description | Selected |
|--------|-------------|----------|
| 仅 numpy+Pillow（推荐） | 只降级 numpy→2.0.2、Pillow→10.4.0，其他依赖的当前版本均已支持 3.9（FastAPI 0.115、SQLAlchemy 2.0、Pydantic 2.10 等） | ✓ |
| 全量审计所有依赖 | 遍历 requirements.txt 每个包，确认其 Python 3.9 支持状态，必要时降级 | |
| Claude 决定 | 由 Claude 根据实际安装情况判断 | |

**User's choice:** 仅 numpy+Pillow（推荐）
**Notes:** 无

---

## PEP 585 内建泛型处理

| Option | Description | Selected |
|--------|-------------|----------|
| 与注解策略一致（推荐） | 仅替换运行时求值位置（Pydantic schemas、SQLAlchemy models）中的 dict[]/list[] 为 Dict[]/List[]，服务层纯注解保留原样 | ✓ |
| 全量替换 | 统一将所有内建泛型替换为 typing 模块的 Dict/List/Tuple/Set | |
| Claude 决定 | 由 Claude 根据实际情况判断 | |

**User's choice:** 与注解策略一致（推荐）
**Notes:** 无

---

## Claude's Discretion

- 批量替换的工具选择（正则/AST）
- 测试验证执行顺序
- 是否需要 eval_type_backport 依赖

## Deferred Ideas

None
