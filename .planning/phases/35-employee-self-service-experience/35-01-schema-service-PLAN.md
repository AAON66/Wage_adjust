---
phase: 35-employee-self-service-experience
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/app/schemas/performance.py
  - backend/app/services/performance_service.py
  - backend/tests/test_services/test_performance_service.py
autonomous: true
requirements:
  - ESELF-03

must_haves:
  truths:
    - "Pydantic `MyTierResponse` 精确包含 4 字段：`year: int | None`、`tier: Literal[1, 2, 3] | None`、`reason: Literal['insufficient_sample', 'no_snapshot', 'not_ranked'] | None`、`data_updated_at: datetime | None`"
    - "`PerformanceService.get_my_tier(employee_id)` 在 4 个业务分支下返回正确语义不变式：`tier is None → reason 必非空`、`tier in {1,2,3} → reason 必为 None`"
    - "当全库无任何 `PerformanceTierSnapshot` 行时，`get_my_tier` 返回 `{year=None, tier=None, reason='no_snapshot', data_updated_at=None}`"
    - "当命中当前年快照且 `snapshot.insufficient_sample is True` 时，`get_my_tier` 返回 `{year=<当前年>, tier=None, reason='insufficient_sample', data_updated_at=<snapshot.updated_at>}`（tier 映射表不被访问）"
    - "当当前年无快照但存在更早年快照时，`get_my_tier` fallback 到最新年，返回体 `year=<最新有快照年>`"
    - "`snapshot.tiers_json` 的 key 为 `str(UUID)`（Phase 33 engine 输出契约），Service 层 lookup 时使用 `str(employee_id)` 而非 `UUID` 对象"
    - "`snapshot.tiers_json.get(str(employee_id))` 返回 None 或键不存在 → `reason='not_ranked'`；返回 1/2/3 → `tier=<1|2|3>` 且 `reason=None`"
  artifacts:
    - path: "backend/app/schemas/performance.py"
      provides: "MyTierResponse Pydantic 模型（D-04 的 4 字段契约 + Literal 枚举）"
      contains: "class MyTierResponse(BaseModel)"
    - path: "backend/app/services/performance_service.py"
      provides: "PerformanceService.get_my_tier(employee_id) 方法（D-13 全部 5 步逻辑）"
      contains: "def get_my_tier"
    - path: "backend/tests/test_services/test_performance_service.py"
      provides: "7+ 个新 pytest 用例覆盖 4 个分支 + fallback + str(UUID) lookup + 不变式断言"
      contains: "get_my_tier"
  key_links:
    - from: "backend/app/services/performance_service.py:get_my_tier"
      to: "backend/app/schemas/performance.py:MyTierResponse"
      via: "返回 MyTierResponse 实例"
      pattern: "MyTierResponse\\("
    - from: "backend/app/services/performance_service.py:get_my_tier"
      to: "backend/app/models/performance_tier_snapshot.py:PerformanceTierSnapshot"
      via: "select() 读快照 + .tiers_json lookup"
      pattern: "PerformanceTierSnapshot"
---

<objective>
为 Phase 35 建立后端数据契约与 Service 层读路径：在 `backend/app/schemas/performance.py` 新增 `MyTierResponse` Pydantic 模型（CONTEXT.md D-04 的精准 4 字段），在 `backend/app/services/performance_service.py` 新增 `get_my_tier(employee_id)` 方法（D-13 的 5 步 fallback 逻辑），并在 `backend/tests/test_services/test_performance_service.py` 中补齐 ≥ 7 个新用例覆盖全部业务分支。

Purpose: 实现 ESELF-03 后端基础 —— 员工档次读路径的 schema + service。本 plan 不修改 API 层（路由 handler 由 Plan 02 挂载）、不动前端（由 Plan 03/04 处理）。

Output: 1 个新 Pydantic schema（4 字段）+ 1 个新 Service 方法 + 7+ 个新 pytest 用例，服务层永不抛 raw Exception（CLAUDE.md 约束）。
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/phases/35-employee-self-service-experience/35-CONTEXT.md
@.planning/phases/34-performance-management-service-and-api/34-CONTEXT.md
@.planning/phases/33-performance-tier-engine/33-CONTEXT.md
@backend/app/schemas/performance.py
@backend/app/services/performance_service.py
@backend/app/models/performance_tier_snapshot.py
@backend/tests/test_services/test_performance_service.py
@CLAUDE.md

<interfaces>
<!-- 关键类型与契约，Executor 无需再探索 codebase。 -->

From backend/app/models/performance_tier_snapshot.py:
```python
class PerformanceTierSnapshot(UUIDPrimaryKeyMixin, CreatedAtMixin, UpdatedAtMixin, Base):
    __tablename__ = 'performance_tier_snapshots'
    year: Mapped[int]                       # 唯一约束 uq_performance_tier_snapshot_year
    tiers_json: Mapped[dict]                # {str(UUID): 1|2|3|None}  — key 为 str(UUID)
    sample_size: Mapped[int]
    insufficient_sample: Mapped[bool]       # True 时全员 tier=None
    distribution_warning: Mapped[bool]
    actual_distribution_json: Mapped[dict]
    skipped_invalid_grades: Mapped[int]
    # 继承 updated_at: Mapped[datetime]  via UpdatedAtMixin
```

From backend/app/schemas/performance.py（现有 pattern 供参考）:
```python
class TierSummaryResponse(BaseModel):
    year: int
    computed_at: datetime
    sample_size: int
    insufficient_sample: bool
    ...
```

From backend/app/services/performance_service.py（现有 get_tier_summary 供对照）:
```python
def get_tier_summary(self, year: int) -> TierSummaryResponse | None:
    # cache → snapshot → None；本 plan 不走 cache（Deferred Ideas）
    snapshot = self.db.scalar(
        select(PerformanceTierSnapshot).where(PerformanceTierSnapshot.year == year),
    )
    ...
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: 新增 MyTierResponse Pydantic schema</name>
  <files>backend/app/schemas/performance.py</files>
  <read_first>
    - backend/app/schemas/performance.py（确认现有 TierSummaryResponse pattern + ConfigDict 使用）
    - .planning/phases/35-employee-self-service-experience/35-CONTEXT.md（D-04 精确 4 字段契约）
    - CLAUDE.md（Pydantic v2 规范 + `from __future__ import annotations`）
  </read_first>
  <behavior>
    - MyTierResponse 能序列化所有 4 分支返回体：tier=1/2/3 + 3 种 reason 组合
    - year / tier / reason / data_updated_at 全部接受 None
    - tier 仅接受 1/2/3 Literal；reason 仅接受 3 个字面量之一
  </behavior>
  <action>
在 `backend/app/schemas/performance.py` 文件中（已有 `TierSummaryResponse` 的同一文件），在 `AvailableYearsResponse` 之后追加一个新类 `MyTierResponse`。

精确写入（从 CONTEXT.md D-04 原样抄录）：

```python
from typing import Literal  # 若文件顶部 import 不含 Literal，补齐此 import


class MyTierResponse(BaseModel):
    """Phase 35 ESELF-03: 员工自助档次响应（D-04 精简 4 字段契约）。

    语义不变式（Service 层保证 + 单测验证）：
      - tier is None → reason 必非空（三种语义：insufficient_sample / no_snapshot / not_ranked）
      - tier in {1, 2, 3} → reason 必为 None

    不引入 display_label 预渲染字段 —— 文案本地化职责归前端（D-04）。
    """

    model_config = ConfigDict(from_attributes=True)

    year: int | None
    tier: Literal[1, 2, 3] | None
    reason: Literal['insufficient_sample', 'no_snapshot', 'not_ranked'] | None
    data_updated_at: datetime | None
```

**明确禁止：**
- 不要添加 `display_label`、`as_of`、`percentile`、`rank` 等字段（D-04 / ESELF-03 / Out of Scope line 94）
- 不要把 `tier` 放成 `int | None` 宽类型 —— 必须 `Literal[1, 2, 3] | None` 以在 OpenAPI schema 里暴露合法值域
- 不要用 `Optional[int]`（项目规范 PEP 604：`int | None`）

文件顶部现有 `from __future__ import annotations` 保留不动。确保 `from pydantic import BaseModel, ConfigDict, Field` 已存在；如无 `Literal` import 则在 `from datetime import datetime` 下一行新增 `from typing import Literal`。
  </action>
  <verify>
    <automated>cd /Users/mac/PycharmProjects/Wage_adjust && .venv/bin/python -c "from backend.app.schemas.performance import MyTierResponse; m = MyTierResponse(year=2026, tier=1, reason=None, data_updated_at=None); assert m.tier == 1; m2 = MyTierResponse(year=None, tier=None, reason='no_snapshot', data_updated_at=None); assert m2.reason == 'no_snapshot'; print('MyTierResponse OK')"</automated>
  </verify>
  <acceptance_criteria>
    - `grep -n "class MyTierResponse(BaseModel):" backend/app/schemas/performance.py` 命中 1 行
    - `grep -n "Literal\[1, 2, 3\] | None" backend/app/schemas/performance.py` 命中（tier 字段）
    - `grep -n "Literal\['insufficient_sample', 'no_snapshot', 'not_ranked'\] | None" backend/app/schemas/performance.py` 命中（reason 字段）
    - `grep -n "data_updated_at: datetime | None" backend/app/schemas/performance.py` 命中
    - `grep -n "year: int | None" backend/app/schemas/performance.py` 命中
    - `grep -cE "display_label|percentile|rank|as_of" backend/app/schemas/performance.py` 输出 0（Out of Scope 字段不得出现于 MyTierResponse 周边）
    - `grep -n "from typing import Literal" backend/app/schemas/performance.py` 命中（或本文件早已含 Literal import）
  </acceptance_criteria>
  <done>MyTierResponse 类存在于 schemas/performance.py；字段顺序与 Literal 签名与 D-04 完全一致；module 可 import 无 error。</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: 新增 PerformanceService.get_my_tier 方法</name>
  <files>backend/app/services/performance_service.py</files>
  <read_first>
    - backend/app/services/performance_service.py（get_tier_summary 216-242 + _snapshot_to_summary 379-415 pattern）
    - backend/app/models/performance_tier_snapshot.py（字段结构确认）
    - .planning/phases/35-employee-self-service-experience/35-CONTEXT.md（D-13 五步逻辑 + D-03 reason 分层）
    - backend/app/schemas/performance.py（引用 Task 1 新建的 MyTierResponse）
    - CLAUDE.md（Service 层不抛 raw Exception；typing 规范）
  </read_first>
  <behavior>
    - 分支 A：全库无快照 → `MyTierResponse(year=None, tier=None, reason='no_snapshot', data_updated_at=None)`
    - 分支 B：当前年有快照且 `insufficient_sample=True` → `MyTierResponse(year=<current>, tier=None, reason='insufficient_sample', data_updated_at=<snapshot.updated_at>)`
    - 分支 C：当前年有快照且 `tiers_json[str(employee_id)] in {1,2,3}` → `MyTierResponse(year=<current>, tier=<1|2|3>, reason=None, data_updated_at=<snapshot.updated_at>)`
    - 分支 D：当前年有快照且 `tiers_json[str(employee_id)] is None` 或 key 不存在 → `MyTierResponse(year=<current>, tier=None, reason='not_ranked', data_updated_at=<snapshot.updated_at>)`
    - 分支 E (fallback)：当前年无快照但 `SELECT ... ORDER BY year DESC LIMIT 1` 命中 → 用最新年快照，走上面 B/C/D 其一
    - UUID lookup：调用方传 `UUID` 对象时，Service 层内部 `str(employee_id)` 才能命中 `tiers_json` 的字符串 key
  </behavior>
  <action>
在 `backend/app/services/performance_service.py` 中新增方法 `get_my_tier`。放置位置：紧接现有 `get_tier_summary` 方法之后（`_ensure_snapshot_row` 之前），保持读路径方法聚合（CONTEXT.md Integration Points line 206）。

**首先检查 imports：** 确认文件顶部已 import `MyTierResponse`。若未 import，在 `from backend.app.schemas.performance import (...)` 的 import 列表中追加 `MyTierResponse`。同时确认 `from datetime import date, datetime, timezone` 存在（已有）。

**方法签名与注释：**

```python
    # ------------------------------------------------------------------
    # get_my_tier (Phase 35 ESELF-03 / D-13)
    # ------------------------------------------------------------------

    def get_my_tier(self, employee_id: str) -> MyTierResponse:
        """员工自助档次查询（Phase 35 ESELF-03）。

        D-01 年份定位策略：
          1. 先查 `PerformanceTierSnapshot.year == datetime.now().year`
          2. 未命中 fallback 到 `ORDER BY year DESC LIMIT 1`
          3. 仍无 → 返回 `{year=None, tier=None, reason='no_snapshot', data_updated_at=None}`

        D-03 三种 tier=None 语义分层：
          - insufficient_sample: 命中快照 && snapshot.insufficient_sample is True
          - no_snapshot:         全库完全无 snapshot 行
          - not_ranked:          命中快照 && 非 insufficient_sample && tiers_json 无此员工或值为 None

        Args:
            employee_id: 员工 UUID 字符串；Service 层用 str() 规范化以匹配
                tiers_json 的 str(UUID) key（Phase 33 engine 输出契约）

        Returns:
            MyTierResponse with invariants:
              - tier is None → reason is not None
              - tier in {1, 2, 3} → reason is None
        """
        # Step 1: 当前年快照
        current_year = datetime.now().year
        snapshot = self.db.scalar(
            select(PerformanceTierSnapshot).where(
                PerformanceTierSnapshot.year == current_year,
            )
        )

        # Step 2: fallback 到最新有快照年
        if snapshot is None:
            snapshot = self.db.scalar(
                select(PerformanceTierSnapshot)
                .order_by(PerformanceTierSnapshot.year.desc())
                .limit(1)
            )

        # Step 3: 全库无快照
        if snapshot is None:
            return MyTierResponse(
                year=None,
                tier=None,
                reason='no_snapshot',
                data_updated_at=None,
            )

        # Step 4: insufficient_sample 分支（全员 null）
        if snapshot.insufficient_sample:
            return MyTierResponse(
                year=snapshot.year,
                tier=None,
                reason='insufficient_sample',
                data_updated_at=snapshot.updated_at,
            )

        # Step 5: 从 tiers_json 查本员工 —— key 是 str(UUID)（Phase 33 契约）
        tiers_map = snapshot.tiers_json or {}
        raw_tier = tiers_map.get(str(employee_id))

        if raw_tier in (1, 2, 3):
            return MyTierResponse(
                year=snapshot.year,
                tier=raw_tier,
                reason=None,
                data_updated_at=snapshot.updated_at,
            )

        # not_ranked: key 不存在 / 值为 None / 值非 1/2/3
        return MyTierResponse(
            year=snapshot.year,
            tier=None,
            reason='not_ranked',
            data_updated_at=snapshot.updated_at,
        )
```

**明确禁止：**
- 不要走 Redis cache（Deferred Ideas：「本期读库即可」）
- 不要 raise 任何异常 —— 所有分支都返回 `MyTierResponse`；未绑定员工 / 员工不存在这类错误在 API 层处理（Plan 02）
- 不要用 `UUID(employee_id)` 再转回 —— 入参就是 str 语义，直接 `str(employee_id)` 兼容 `UUID` 对象入参（Python 的 `str(uuid_obj)` 返回标准格式）
- 不要依赖 `self.cache.get_my_tier(...)` —— `TierCache` 只有 per-year summary 接口，不做 per-employee 缓存
- 不要改 `_snapshot_to_summary` —— 那是 HR 端 TierSummaryResponse 用的，和 MyTierResponse 不同

**如果 snapshot.updated_at 是 naive datetime（SQLite 可能）：** 不做 tz 归一化 —— Pydantic v2 接受 naive datetime 序列化为 ISO 字符串；前端 `new Date(iso)` 按本地时区解析。保持与 `_snapshot_to_summary` 同文件风格差异（那里因为 `TierSummaryResponse.computed_at` 是非 null 才补 tz）。
  </action>
  <verify>
    <automated>cd /Users/mac/PycharmProjects/Wage_adjust && .venv/bin/python -c "from backend.app.services.performance_service import PerformanceService; import inspect; assert 'get_my_tier' in [m[0] for m in inspect.getmembers(PerformanceService, predicate=inspect.isfunction)]; sig = inspect.signature(PerformanceService.get_my_tier); assert 'employee_id' in sig.parameters; print('get_my_tier method OK')"</automated>
  </verify>
  <acceptance_criteria>
    - `grep -n "def get_my_tier(self, employee_id: str) -> MyTierResponse:" backend/app/services/performance_service.py` 命中 1 行
    - `grep -n "MyTierResponse" backend/app/services/performance_service.py` 至少 5 行命中（import + 4 个 return 语句）
    - `grep -n "reason='no_snapshot'" backend/app/services/performance_service.py` 命中
    - `grep -n "reason='insufficient_sample'" backend/app/services/performance_service.py` 命中
    - `grep -n "reason='not_ranked'" backend/app/services/performance_service.py` 命中
    - `grep -n "str(employee_id)" backend/app/services/performance_service.py` 命中（tiers_json lookup）
    - `grep -nE "ORDER BY year DESC|order_by\(PerformanceTierSnapshot\.year\.desc\(\)\)" backend/app/services/performance_service.py` 命中（fallback 语句）
    - `grep -cE "raise (Exception|ValueError|HTTPException)" backend/app/services/performance_service.py` 的数量与改动前保持不变（本方法不新增 raise）
  </acceptance_criteria>
  <done>get_my_tier 方法存在于 PerformanceService；5 步逻辑齐全；4 个 return MyTierResponse 调用与 D-03/D-13 语义一致；文件其他方法未被改动。</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Service 层 pytest 覆盖 ≥ 7 用例</name>
  <files>backend/tests/test_services/test_performance_service.py</files>
  <read_first>
    - backend/tests/test_services/test_performance_service.py（现有 fixtures + `_make_records` helper + SQLite 会话构造模式）
    - backend/app/services/performance_service.py（Task 2 新增 get_my_tier）
    - backend/app/models/performance_tier_snapshot.py（字段 + 唯一约束）
    - .planning/phases/35-employee-self-service-experience/35-CONTEXT.md（D-13 + specifics line 224）
  </read_first>
  <behavior>
    - 覆盖全部 4 业务分支 + fallback + str(UUID) lookup + invariants
  </behavior>
  <action>
在 `backend/tests/test_services/test_performance_service.py` 文件末尾追加一个新 section（加分隔注释 `# ==== Phase 35 ESELF-03: get_my_tier 用例 ====`）并写入以下 ≥ 7 个测试函数。复用文件中已有的 session / employee_factory / `_make_records` 等 fixture（完整 fixture 名称看文件顶部）。

**若文件当前使用 pytest fixture 风格 + SQLAlchemy 会话，照搬现有风格（不引入新的 conftest.py）。** 具体用例：

```python
# ==== Phase 35 ESELF-03: get_my_tier 用例 ====

from uuid import uuid4, UUID
from backend.app.schemas.performance import MyTierResponse


def test_get_my_tier_returns_no_snapshot_when_db_empty(db, employee_factory):
    """分支 A：全库无任何 PerformanceTierSnapshot → reason='no_snapshot'。"""
    emp = employee_factory(employee_no='E001')
    service = PerformanceService(db)
    result = service.get_my_tier(str(emp.id))
    assert isinstance(result, MyTierResponse)
    assert result.year is None
    assert result.tier is None
    assert result.reason == 'no_snapshot'
    assert result.data_updated_at is None


def test_get_my_tier_returns_insufficient_sample_when_flag_true(db, employee_factory):
    """分支 B：当前年快照 insufficient_sample=True → reason='insufficient_sample'，tier=None。"""
    from datetime import datetime
    current_year = datetime.now().year
    emp = employee_factory(employee_no='E002')
    snap = PerformanceTierSnapshot(
        year=current_year,
        tiers_json={},
        sample_size=5,
        insufficient_sample=True,
        distribution_warning=False,
        actual_distribution_json={},
        skipped_invalid_grades=0,
    )
    db.add(snap); db.commit(); db.refresh(snap)
    service = PerformanceService(db)
    result = service.get_my_tier(str(emp.id))
    assert result.year == current_year
    assert result.tier is None
    assert result.reason == 'insufficient_sample'
    assert result.data_updated_at is not None
    assert result.data_updated_at == snap.updated_at


def test_get_my_tier_returns_tier_when_employee_in_tiers_json(db, employee_factory):
    """分支 C：当前年快照命中 + tiers_json[str(uuid)] == 2 → tier=2, reason=None。"""
    from datetime import datetime
    current_year = datetime.now().year
    emp = employee_factory(employee_no='E003')
    snap = PerformanceTierSnapshot(
        year=current_year,
        tiers_json={str(emp.id): 2},
        sample_size=100,
        insufficient_sample=False,
        distribution_warning=False,
        actual_distribution_json={'1': 0.2, '2': 0.7, '3': 0.1},
        skipped_invalid_grades=0,
    )
    db.add(snap); db.commit()
    service = PerformanceService(db)
    result = service.get_my_tier(str(emp.id))
    assert result.year == current_year
    assert result.tier == 2
    assert result.reason is None


def test_get_my_tier_accepts_uuid_object_and_stringifies_key(db, employee_factory):
    """str(UUID) lookup：调用方传 UUID 对象时，内部 str(employee_id) 匹配 tiers_json str key。"""
    from datetime import datetime
    current_year = datetime.now().year
    emp = employee_factory(employee_no='E004')
    emp_uuid = UUID(emp.id) if isinstance(emp.id, str) else emp.id
    snap = PerformanceTierSnapshot(
        year=current_year,
        tiers_json={str(emp.id): 1},
        sample_size=80,
        insufficient_sample=False,
        distribution_warning=False,
        actual_distribution_json={'1': 0.25, '2': 0.65, '3': 0.10},
        skipped_invalid_grades=0,
    )
    db.add(snap); db.commit()
    service = PerformanceService(db)
    # 传 UUID 对象也应命中
    result_uuid = service.get_my_tier(emp_uuid)
    assert result_uuid.tier == 1
    # 传 str 也应命中
    result_str = service.get_my_tier(str(emp.id))
    assert result_str.tier == 1


def test_get_my_tier_returns_not_ranked_when_key_missing(db, employee_factory):
    """分支 D-1：key 不存在于 tiers_json → reason='not_ranked'。"""
    from datetime import datetime
    current_year = datetime.now().year
    emp = employee_factory(employee_no='E005')
    other_emp = employee_factory(employee_no='E006')
    snap = PerformanceTierSnapshot(
        year=current_year,
        tiers_json={str(other_emp.id): 1},  # 仅 other，不含 emp
        sample_size=60,
        insufficient_sample=False,
        distribution_warning=False,
        actual_distribution_json={'1': 0.2, '2': 0.7, '3': 0.1},
        skipped_invalid_grades=0,
    )
    db.add(snap); db.commit()
    service = PerformanceService(db)
    result = service.get_my_tier(str(emp.id))
    assert result.year == current_year
    assert result.tier is None
    assert result.reason == 'not_ranked'
    assert result.data_updated_at is not None


def test_get_my_tier_returns_not_ranked_when_value_is_none(db, employee_factory):
    """分支 D-2：tiers_json[str(uuid)] is None → reason='not_ranked'。"""
    from datetime import datetime
    current_year = datetime.now().year
    emp = employee_factory(employee_no='E007')
    snap = PerformanceTierSnapshot(
        year=current_year,
        tiers_json={str(emp.id): None},
        sample_size=60,
        insufficient_sample=False,
        distribution_warning=False,
        actual_distribution_json={},
        skipped_invalid_grades=0,
    )
    db.add(snap); db.commit()
    service = PerformanceService(db)
    result = service.get_my_tier(str(emp.id))
    assert result.tier is None
    assert result.reason == 'not_ranked'


def test_get_my_tier_falls_back_to_latest_year_when_current_missing(db, employee_factory):
    """分支 E (fallback)：当前年无快照 → 使用 ORDER BY year DESC 最新年快照。"""
    from datetime import datetime
    current_year = datetime.now().year
    older_year = current_year - 2  # 绝对不等于 current_year
    emp = employee_factory(employee_no='E008')
    snap = PerformanceTierSnapshot(
        year=older_year,
        tiers_json={str(emp.id): 3},
        sample_size=50,
        insufficient_sample=False,
        distribution_warning=False,
        actual_distribution_json={'1': 0.2, '2': 0.7, '3': 0.1},
        skipped_invalid_grades=0,
    )
    db.add(snap); db.commit()
    service = PerformanceService(db)
    result = service.get_my_tier(str(emp.id))
    assert result.year == older_year  # ← fallback 到旧年
    assert result.tier == 3
    assert result.reason is None


def test_get_my_tier_invariant_tier_implies_reason_none(db, employee_factory):
    """不变式：tier in {1,2,3} → reason 必为 None（D-04 契约）。"""
    from datetime import datetime
    current_year = datetime.now().year
    emp = employee_factory(employee_no='E009')
    snap = PerformanceTierSnapshot(
        year=current_year,
        tiers_json={str(emp.id): 2},
        sample_size=100,
        insufficient_sample=False,
        distribution_warning=False,
        actual_distribution_json={},
        skipped_invalid_grades=0,
    )
    db.add(snap); db.commit()
    service = PerformanceService(db)
    result = service.get_my_tier(str(emp.id))
    assert result.tier in {1, 2, 3}
    assert result.reason is None, f'tier={result.tier} 时 reason 必须为 None'
```

**重要兼容性说明：** 如果现有文件中 `db` / `employee_factory` fixture 名称不同，先 grep `def db(` 和 `def employee_factory(` 来确认实际名字，再按照实际签名调整用例参数。不要把 fixture 参数名改写为随便新名字。

若 `Task 1` 的 `MyTierResponse` import 放在文件靠上，可把 `from backend.app.schemas.performance import MyTierResponse` 放到 test 文件顶部既有 imports 同 block。

**禁止：**
- 不要 mock `self.db` —— 用真实 SQLite session（延续文件 Phase 34 pattern）
- 不要写「若方法不存在就跳过」的 try/except —— Task 2 必然已交付该方法
- 不要把 PerformanceTierSnapshot 写入同一 year 两次（违反 uq_performance_tier_snapshot_year）
  </action>
  <verify>
    <automated>cd /Users/mac/PycharmProjects/Wage_adjust && .venv/bin/python -m pytest backend/tests/test_services/test_performance_service.py -k get_my_tier -v --no-header 2>&1 | tail -30</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "^def test_get_my_tier" backend/tests/test_services/test_performance_service.py` 输出 ≥ 7
    - `pytest backend/tests/test_services/test_performance_service.py -k get_my_tier` 退出码 0
    - `grep -n "reason == 'no_snapshot'" backend/tests/test_services/test_performance_service.py` 命中
    - `grep -n "reason == 'insufficient_sample'" backend/tests/test_services/test_performance_service.py` 命中
    - `grep -n "reason == 'not_ranked'" backend/tests/test_services/test_performance_service.py` 命中
    - `grep -n "falls_back_to_latest_year" backend/tests/test_services/test_performance_service.py` 命中（fallback 用例）
    - `grep -n "accepts_uuid_object_and_stringifies_key" backend/tests/test_services/test_performance_service.py` 命中（str(UUID) 用例）
  </acceptance_criteria>
  <done>≥ 7 个新 pytest 用例全部通过；覆盖 A/B/C/D/E 五分支 + str(UUID) lookup + invariants。</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| API caller → Service | 本 plan 不直接受 HTTP 输入，Service 层 `employee_id` 参数由 Plan 02 从 `current_user.employee_id`（JWT subject）派生；本 plan 保证 Service 层对任意 employee_id 都只返回该员工的 tier，不返回其他员工数据 |
| Service → DB | 查询仅 SELECT，无写路径，无 SQL 注入面（使用 SQLAlchemy `select(...).where(col == value)` 参数化） |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-35-01-01 | I (Info Disclosure) | get_my_tier 返回体 | mitigate | MyTierResponse 只有 4 字段（year / tier / reason / data_updated_at），schema 层面物理不可能泄露其他员工 id、具体排名、百分位、同档名单（ESELF-03 + REQUIREMENTS.md line 89-103 合规红线）。Task 1 acceptance criteria 含负向检查 `grep -cE "display_label\|percentile\|rank\|as_of"` 必须为 0 |
| T-35-01-02 | T (Tampering) | tiers_json lookup | mitigate | Service 层只读 snapshot 行，无写操作；tiers_json 来源是 Phase 33 Engine 输出 + Phase 34 Service 写入，本 plan 不修改这条写路径，延续既有审计链（tiers_json 改动要经过 `recompute_tiers` 的行锁） |
| T-35-01-03 | I (Info Disclosure) | fallback 到最旧年 | mitigate | 响应体必带 `year` 字段（D-01），前端显式渲染「YYYY 年度档次」，员工可见数据年份来源，不会误以为是当前数据；Task 2 acceptance 验证 `grep "year=snapshot.year"` |
| T-35-01-04 | D (Denial of Service) | fallback 查询性能 | accept | `performance_tier_snapshots` 表每年 1 行（Phase 34 D-01），预期全生命周期 < 20 行；`SELECT ... ORDER BY year DESC LIMIT 1` 查询成本 O(N) 上可忽略；无需索引优化 |
| T-35-01-05 | S (Spoofing) | employee_id 入参伪造 | transfer | 本 Service 层方法相信入参；防伪由 API 层（Plan 02）`Depends(get_current_user)` + `current_user.employee_id` 保证，JWT 有效性由 `decode_token` 校验 |
</threat_model>

<verification>
- `pytest backend/tests/test_services/test_performance_service.py -k get_my_tier` 通过（≥ 7 用例）
- `python -c "from backend.app.schemas.performance import MyTierResponse; from backend.app.services.performance_service import PerformanceService; print('imports OK')"` 无报错
- `grep` 静态断言全部通过（见各 task acceptance_criteria）
- CLAUDE.md 约束：文件顶部 `from __future__ import annotations` 保留；`MyTierResponse` 使用 PEP 604 `int | None` 风格；Service 层零 raw Exception raise
</verification>

<success_criteria>
1. `backend/app/schemas/performance.py` 含 `MyTierResponse` 类，4 字段与 D-04 完全一致
2. `backend/app/services/performance_service.py` 含 `get_my_tier(employee_id)` 方法，5 步逻辑与 D-13 完全一致
3. `backend/tests/test_services/test_performance_service.py` 含 ≥ 7 个新 `test_get_my_tier_*` 用例，全部通过
4. 负向断言：schema 无 `display_label` / `percentile` / `rank` / `as_of` 字段
5. 本 plan 不动 API 层、不动前端 —— `grep` 验证 `backend/app/api/v1/performance.py` 第 206-209 行 TODO 注释保留（由 Plan 02 删除）
</success_criteria>

<output>
After completion, create `.planning/phases/35-employee-self-service-experience/35-01-SUMMARY.md`
</output>
