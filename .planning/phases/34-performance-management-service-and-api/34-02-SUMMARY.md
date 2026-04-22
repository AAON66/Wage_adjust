---
phase: 34-performance-management-service-and-api
plan: 02
subsystem: backend/services + backend/core/config
tags: [services, config, cache, redis, exceptions, phase-34, wave-1]
requirements-completed: [PERF-05]
dependency-graph:
  requires: []
  provides:
    - Settings.performance_tier_redis_prefix / _ttl_seconds / _recompute_timeout_seconds 三字段（D-02 / D-03）
    - TierCache 类（4 方法：cache_key / get_cached / set_cached / invalidate；优雅降级）
    - TierRecomputeBusyError / TierRecomputeFailedError 自定义业务异常（D-05 / D-06）
  affects:
    - Phase 34 Plan 03 (Service 层) 直接 import TierCache + 两个异常类，无需再处理 Redis 异常
    - Phase 34 Plan 04 (UI 层) 不直接依赖；通过 Service 间接消费
tech-stack:
  added:
    - backend/app/services/tier_cache.py（首个独立缓存封装类）
    - backend/app/services/exceptions.py（首个 service 层自定义异常聚合模块）
    - 3 个 Settings 字段（全部 env 可覆盖）
  patterns:
    - 构造函数注入（redis.Redis + Settings）— 与 EvaluationService / SalaryService 一致的 testability 风格
    - Redis 优雅降级（catch redis.RedisError → 降级 + warn log，不向上层抛 ConnectionError）
    - service 层异常类继承自内置 Exception（不依赖 fastapi.HTTPException），保持 service ↔ web 解耦
key-files:
  created:
    - backend/app/services/tier_cache.py（67 行）
    - backend/app/services/exceptions.py（25 行）
    - backend/tests/test_services/test_tier_cache.py（112 行，12 用例）
  modified:
    - backend/app/core/config.py（+5 行：3 个 Settings 字段 + 1 行注释）
    - .env.example（+8 行：3 个 env 键的注释与默认值）
key-decisions:
  - service 层与 fastapi 完全解耦：exceptions.py 不 import HTTPException；TierCache 不 import 任何 web 层符号
  - Redis 优雅降级而非抛错：缓存层不可用 → 上层一律走表层 fallback（即使 5 秒重算超时也不影响数据可读性）
  - 构造函数注入 redis.Redis 而非内部调 get_redis()：单测可注入 MagicMock，零网络依赖
  - 接受 redis_client=None 作为合法状态（环境未配置 Redis 时 service 仍可运行，纯走 DB 路径）
  - JSON 编码用 default=str：兼容 datetime 等 Pydantic 经常返回的非 JSON 原生类型
  - get_cached 在 invalid JSON 时返回 None + warn log（而非抛错）：旧/坏缓存被自动旁路，不阻塞业务
metrics:
  start-time: 2026-04-22T08:00:00Z
  end-time: 2026-04-22T08:08:37Z
  duration-seconds: 517
  duration-human: ~9 分钟
  tasks-completed: 2 / 2
  files-created: 3
  files-modified: 2
  tests-added: 12
  tests-pass-rate: 12/12 (100%)
  regressions: 0 (engines 64/64 pass)
---

# Phase 34 Plan 02: TierCache + 自定义异常 + Settings 配置化 Summary

为 Phase 34-03 Service 层提供 3 块独立基础设施：① 配置化的 Redis cache 参数（prefix / TTL / recompute timeout，全部 env 可覆盖）；② 一个细粒度封装的 `TierCache` 类（4 公开方法 + Redis 不可达优雅降级路径）；③ 两个自定义业务异常类（`TierRecomputeBusyError` / `TierRecomputeFailedError`），让 Service 层抛业务语义异常、API 层 catch 后转 HTTP 状态码，service 层与 web 层完全解耦。

## What Got Built

### Task 1: Settings 字段 + .env.example + exceptions 模块（commit `0bcd945`）

**`backend/app/core/config.py`**：在 Phase 33 引入的 `performance_tier_min_sample_size` 之后追加 3 个新字段，全部继承 `BaseSettings.case_sensitive=False`，可通过 env 直接覆盖：

```python
# Performance tier cache & recompute (Phase 34 D-02 / D-03)
performance_tier_redis_prefix: str = 'tier_summary'
performance_tier_redis_ttl_seconds: int = 86_400
performance_tier_recompute_timeout_seconds: int = 5
```

**`.env.example`**：在「ELIGIBILITY / PERFORMANCE THRESHOLDS」段尾追加新段，含 3 个键的注释与默认值（`PERFORMANCE_TIER_REDIS_PREFIX` / `PERFORMANCE_TIER_REDIS_TTL_SECONDS` / `PERFORMANCE_TIER_RECOMPUTE_TIMEOUT_SECONDS`），便于运维直接复制成 .env。

**`backend/app/services/exceptions.py`**（新建）：导出两个自定义异常类，均继承自内置 `Exception`：

- `TierRecomputeBusyError(year, message=None)` — `__init__` 设置 `self.year`；默认消息 `f'Tier recompute busy for year {year}'`。Service 抛 → API 层转 409 Conflict + retry_after_seconds=5。
- `TierRecomputeFailedError(year, cause)` — `__init__` 设置 `self.year` + `self.cause`；消息 `f'Tier recompute failed for year {year}: {cause}'`。手动 recompute 路径由 API 层转 422；自动重算路径由调用方 silently log。

**严格遵守**：模块顶部不 import HTTPException 或 fastapi 任何符号 — service 层与 web 层零耦合。

### Task 2: TierCache 类 + 12 个 pytest 用例（commit `f2b733f`）

**`backend/app/services/tier_cache.py`**（新建）：单一职责类 `TierCache`，构造函数：

```python
def __init__(self, redis_client: redis.Redis | None, settings: Settings) -> None
```

注入 `redis_client` 而非内部 `get_redis()` 调用 — 单测注入 `MagicMock` 即可零网络验证；同时 `redis_client=None` 是合法状态（环境无 Redis 时 service 仍可运行）。

**4 个公开方法：**

| Method | 行为 | 异常路径 |
|--------|------|----------|
| `cache_key(year) -> str` | 拼接 `f'{prefix}:{year}'` | 无 |
| `get_cached(year) -> dict \| None` | redis.get → JSON decode → dict；miss / decode error → None | RedisError → warn + None |
| `set_cached(year, payload)` | redis.set(key, json.dumps(payload, default=str), ex=TTL) | RedisError → warn + noop |
| `invalidate(year)` | redis.delete(key) | RedisError → warn + noop |

**优雅降级核心**：Redis 不可达时三个 mutator 全部 catch `redis.RedisError` → warn log → 静默返回（get→None / set/invalidate→noop）。上层永远不需要 try/except `ConnectionError`，永远走表层 fallback。

**`backend/tests/test_services/test_tier_cache.py`**（新建，12 用例）：

| # | Test | 覆盖点 |
|---|------|--------|
| 1 | `test_cache_key_default_prefix` | cache key 拼接（默认 prefix=tier_summary） |
| 2 | `test_cache_key_custom_prefix` | cache key 拼接（Settings(prefix='foo')） |
| 3 | `test_set_cached_uses_default_ttl` | set 时 ex=86400（默认 TTL） |
| 4 | `test_set_cached_uses_custom_ttl` | set 时 ex=10（Settings 覆盖 TTL） |
| 5 | `test_get_cached_returns_decoded_dict` | redis 返回 JSON 字符串 → 解析 dict 返回 |
| 6 | `test_get_cached_returns_none_on_miss` | redis 返回 None → 返回 None |
| 7 | `test_invalidate_calls_redis_delete` | invalidate 调 redis.delete(正确 key) |
| 8 | `test_get_silent_on_redis_unavailable` | RedisConnectionError on get → 返回 None（不抛） |
| 9 | `test_set_silent_on_redis_unavailable` | RedisConnectionError on set → noop（不抛） |
| 10 | `test_invalidate_silent_on_redis_unavailable` | RedisConnectionError on invalidate → noop（不抛） |
| 11 | `test_redis_client_none_returns_none_no_op` | redis_client=None → 全方法不抛 |
| 12 | `test_get_cached_returns_none_on_invalid_json` | 缓存写坏（非合法 JSON）→ 返回 None + warn |

`pytest backend/tests/test_services/test_tier_cache.py -v` → **12 passed in 0.05s**。
`pytest backend/tests/test_engines/ -x` → **64 passed**，零回归。

## Phase 34-03 Service 层接口契约

Wave 2 Plan 03 可直接消费如下符号，零适配层：

```python
from backend.app.services.tier_cache import TierCache
from backend.app.services.exceptions import (
    TierRecomputeBusyError,
    TierRecomputeFailedError,
)
from backend.app.core.config import Settings, get_settings
from backend.app.core.redis import get_redis

# Service 构造（PerformanceService.__init__）：
def __init__(self, db: Session, settings: Settings) -> None:
    self._db = db
    self._settings = settings
    try:
        self._cache = TierCache(get_redis(), settings)
    except redis.ConnectionError:
        self._cache = TierCache(None, settings)  # 优雅降级

# 读路径 get_tier_summary(year)：
def get_tier_summary(self, year: int) -> TierSummary | None:
    cached = self._cache.get_cached(year)
    if cached is not None:
        return TierSummary.model_validate(cached)
    snapshot = self._query_snapshot(year)
    if snapshot is None:
        return None
    payload = self._snapshot_to_payload(snapshot)
    self._cache.set_cached(year, payload)
    return TierSummary.model_validate(payload)

# 写路径 recompute_tiers(year)：
def recompute_tiers(self, year: int) -> TierSummary:
    self._cache.invalidate(year)  # invalidate 在前
    try:
        result = self._engine.assign(...)  # PerformanceTierEngine（Phase 33）
        self._upsert_snapshot(year, result)
    except OperationalError as exc:  # FOR UPDATE NOWAIT 失败
        if 'lock' in str(exc).lower():
            raise TierRecomputeBusyError(year) from exc
        raise TierRecomputeFailedError(year, str(exc)) from exc
    payload = self._snapshot_to_payload(self._query_snapshot(year))
    self._cache.set_cached(year, payload)  # set 在后（写穿透）
    return TierSummary.model_validate(payload)
```

**API 层 catch 模板：**

```python
@router.post('/recompute-tiers')
def recompute_tiers(year: int, ...):
    try:
        return service.recompute_tiers(year)
    except TierRecomputeBusyError as exc:
        raise HTTPException(
            status_code=409,
            detail={'error': 'tier_recompute_busy', 'year': exc.year, 'retry_after_seconds': 5},
        ) from exc
    except TierRecomputeFailedError as exc:
        raise HTTPException(
            status_code=422,
            detail={'error': 'tier_recompute_failed', 'year': exc.year, 'cause': exc.cause},
        ) from exc
```

## Deviations from Plan

**Plan 要求最小 8 个测试用例，实际交付 12 个（+50%）**：在 plan 列出的 10 + 1 None client 兜底之外，自发加了 1 条边界用例 `test_get_cached_returns_none_on_invalid_json`，覆盖坏缓存自动旁路场景。这是 Rule 2（auto-add missing critical functionality）— `json.loads` 抛 ValueError 时缓存层若不 catch 就会向上传染，违反 service ↔ web 解耦原则。代码 already had `try/except (TypeError, ValueError)` 防护，测试只是补齐验证。

无其他偏离 — Plan 1:1 落地。

## Verification

| 检查项 | 命令 | 结果 |
|--------|------|------|
| Settings 3 字段默认值 | `python -c "from backend.app.core.config import Settings; ..."` | OK |
| TierRecomputeBusyError 实例 .year 属性 | 同上 | OK |
| TierCache 单测全绿 | `pytest backend/tests/test_services/test_tier_cache.py -v` | 12 passed |
| Service 层不 import fastapi | `grep -E "^from fastapi\|^import fastapi" tier_cache.py` | 无输出 |
| TierCache 零 raise（优雅降级） | `grep -E "^\s*raise\s" tier_cache.py` | 无输出 |
| engines 全套无回归 | `pytest backend/tests/test_engines/ -x` | 64 passed |

## Self-Check

**Created files exist:**
- FOUND: backend/app/services/tier_cache.py
- FOUND: backend/app/services/exceptions.py
- FOUND: backend/tests/test_services/test_tier_cache.py

**Commits exist:**
- FOUND: 0bcd945 (Task 1)
- FOUND: f2b733f (Task 2)

## Self-Check: PASSED
