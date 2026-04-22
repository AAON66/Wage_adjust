---
phase: 35-employee-self-service-experience
plan: 02
type: execute
wave: 1
depends_on:
  - 35-01
files_modified:
  - backend/app/api/v1/performance.py
  - backend/tests/test_api/test_performance_api.py
autonomous: true
requirements:
  - ESELF-03

must_haves:
  truths:
    - "`GET /api/v1/performance/me/tier` 在绑定员工的任意角色（admin/hrbp/manager/employee）下均返回 200 + MyTierResponse 结构"
    - "未绑定员工（`current_user.employee_id is None`）调用 `/me/tier` 返回 422 + 中文 detail '您尚未绑定员工信息'"
    - "JWT 有效但 `Employee` 行被删除时，调用 `/me/tier` 返回 404 + 中文 detail '员工档案缺失'"
    - "`/performance/me/tier` 无任何 path/query 参数，URL 只能定位到 JWT subject 本人（ESELF-04 横向越权天然不可达）"
    - "`/performance/me/tier` 路由注册顺序在其他 `/performance` 路由之后 —— FastAPI 不会把字符串 `me` 当 `{employee_id}` 捕获（本期 `/performance/records` 无 `/{id}` 变体，但为未来兼容保留一致风格）"
    - "响应体 year 字段非空时前端能拿到准确年份（fallback 年或当前年）"
    - "API 层永不向客户端泄露 stack trace / SQL fragment / 其他员工数据（500 通过 main.py 全局 handler 输出通用消息）"
  artifacts:
    - path: "backend/app/api/v1/performance.py"
      provides: "GET /me/tier handler，替换 206-209 TODO 注释，包含 422/404/200 三分支"
      contains: "@router.get('/me/tier'"
    - path: "backend/tests/test_api/test_performance_api.py"
      provides: "≥ 5 个新 API 测试用例，覆盖 4 角色 happy path + 422 + 404"
      contains: "test_me_tier"
  key_links:
    - from: "backend/app/api/v1/performance.py:@router.get('/me/tier')"
      to: "PerformanceService.get_my_tier(current_user.employee_id)"
      via: "Depends(get_current_user) 注入 User + 取 employee_id"
      pattern: "get_my_tier\\(current_user\\.employee_id\\)"
    - from: "backend/tests/test_api/test_performance_api.py"
      to: "TestClient.get('/api/v1/performance/me/tier', headers=ctx.auth_header(...))"
      via: "JWT Bearer header + 校验 200/422/404 三态"
      pattern: "/api/v1/performance/me/tier"
---

<objective>
挂载 Phase 35 ESELF-03 的 HTTP handler：将 `backend/app/api/v1/performance.py` 第 206-209 行的 `TODO Phase 35` 注释替换为真实 `GET /api/v1/performance/me/tier` 路由，依赖注入 `get_current_user`，调用 Plan 01 交付的 `PerformanceService.get_my_tier`，并实现 D-06 的 422/404/500 错误分支。同时将既有占位测试 `test_me_tier_endpoint_does_not_exist_yet`（现断言 404）改写为真实 5+ 用例。

Purpose: 实现 ESELF-03 的可访问 HTTP 端点。本 plan 不改 Service 层、不改前端；完全消费 Plan 01 的 schema + service。

Output: 1 个新 route handler + 改造后的测试文件（删除占位 + 新增 ≥ 5 个用例）。
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
@.planning/phases/32.1-employee-eligibility-visibility/32.1-CONTEXT.md
@backend/app/api/v1/performance.py
@backend/app/api/v1/eligibility.py
@backend/app/services/performance_service.py
@backend/app/schemas/performance.py
@backend/app/dependencies.py
@backend/app/models/user.py
@backend/tests/test_api/test_performance_api.py
@CLAUDE.md

<interfaces>
<!-- Plan 01 交付的新契约 -->

From backend/app/schemas/performance.py:
```python
class MyTierResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    year: int | None
    tier: Literal[1, 2, 3] | None
    reason: Literal['insufficient_sample', 'no_snapshot', 'not_ranked'] | None
    data_updated_at: datetime | None
```

From backend/app/services/performance_service.py:
```python
def get_my_tier(self, employee_id: str) -> MyTierResponse:
    """D-13 五步逻辑；不 raise，所有分支都返回 MyTierResponse。"""
```

From backend/app/api/v1/eligibility.py (GET /me 参考模板):
```python
@router.get('/me', response_model=EligibilityResultSchema)
def get_my_eligibility(
    ...,
    current_user: User = Depends(get_current_user),
) -> EligibilityResultSchema:
    if current_user.employee_id is None:
        raise HTTPException(status_code=422, detail='您尚未绑定员工信息，请前往「账号设置」完成绑定')
    service = EligibilityService(db)
    # check_employee 在 employee 不存在时 raise HTTPException(404, '员工未找到')
    result = service.check_employee(current_user.employee_id, ...)
    ...
```

From backend/app/dependencies.py:
```python
def get_current_user(token=..., db=..., settings=...) -> User:
    # 返回 User ORM；401 在 token 无效时由此处 raise
```

From backend/app/models/user.py:
```python
class User:
    id: str
    employee_id: str | None  # 可空；未绑定用户此字段为 None
    role: str                # 'admin' / 'hrbp' / 'manager' / 'employee'
```

From backend/app/models/employee.py:
```python
class Employee:
    id: str
    # API 层用 db.get(Employee, employee_id) 校验存在性
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: 挂载 GET /me/tier handler（替换 TODO）</name>
  <files>backend/app/api/v1/performance.py</files>
  <read_first>
    - backend/app/api/v1/performance.py（确认 206-209 当前 TODO 注释 + router prefix + `_make_service` helper）
    - backend/app/api/v1/eligibility.py（GET /me handler 317-358 完整模板）
    - .planning/phases/35-employee-self-service-experience/35-CONTEXT.md（D-06 错误态文案 + D-01 无参数路由）
    - backend/app/services/performance_service.py（get_my_tier 签名）
    - backend/app/schemas/performance.py（MyTierResponse import）
  </read_first>
  <behavior>
    - happy path：返回 200 + MyTierResponse（来自 Service）
    - 未绑定：`current_user.employee_id is None` → 422 + 中文 detail
    - 员工已删：`db.get(Employee, employee_id)` 返回 None → 404 + 中文 detail
    - 任意角色（admin/hrbp/manager/employee）只要 JWT 有效 + 有 employee_id + employee 存在，都能调用成功
  </behavior>
  <action>
在 `backend/app/api/v1/performance.py` 中执行两步：

**Step A — 修改 imports：**

在文件顶部的 import 区，完成以下变更：

1. 在 `from backend.app.dependencies import get_app_settings, get_db, require_roles` 这一行**追加** `get_current_user`，最终形如：
   ```python
   from backend.app.dependencies import get_app_settings, get_current_user, get_db, require_roles
   ```
2. 在 `from backend.app.schemas.performance import (...)` block 追加 `MyTierResponse`（保持字母序）：
   ```python
   from backend.app.schemas.performance import (
       AvailableYearsResponse,
       MyTierResponse,
       PerformanceRecordCreateRequest,
       ...
   )
   ```
3. 新增一行 import：
   ```python
   from backend.app.models.employee import Employee
   from backend.app.models.user import User
   ```
   （放在既有 `from backend.app.dependencies import ...` 之后、schemas import 之前；若已有则不重复）

**Step B — 替换 206-209 行 TODO，挂载真实 handler：**

把现有片段（第 204-209 行）：
```python
# ---------------------------------------------------------------------------
# Phase 35 保留位（本期不实现 handler，仅声明）
# GET /api/v1/performance/me/tier — 员工自助查询本人档次
# TODO Phase 35：在 ESELF-03 范围内交付（员工端档次徽章）
# ---------------------------------------------------------------------------
```

整块删除（包括所有 TODO 注释行），**替换**为以下内容（文件末尾原位）：

```python
# ---------------------------------------------------------------------------
# GET /performance/me/tier — Phase 35 ESELF-03 员工自助档次查询
#
# 无参数路由：actor 由 JWT subject（current_user.employee_id）决定；
# 横向越权天然不可达（ESELF-04 红线；T-35-02-01 mitigation）。
# 任意已登录角色均可调用（admin/hrbp/manager/employee）；
# 不需要 require_roles —— 无 `{employee_id}` 变体即无越权面。
# ---------------------------------------------------------------------------

@router.get('/me/tier', response_model=MyTierResponse)
def get_my_tier(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    current_user: User = Depends(get_current_user),
) -> MyTierResponse:
    """员工自助查询本人绩效档次（Phase 35 ESELF-03）。

    响应 200 + MyTierResponse，覆盖 4 语义分支：
      - tier in {1,2,3} + reason=None：员工有档次
      - tier=None + reason='insufficient_sample'：样本不足
      - tier=None + reason='no_snapshot'：HR 从未录入绩效
      - tier=None + reason='not_ranked'：命中快照但本员工未录绩效

    错误态（D-06）：
      - 未绑定员工 → 422 + '您尚未绑定员工信息'
      - 员工档案被删 → 404 + '员工档案缺失'
      - 其他异常 → 500（main.py 全局 handler）
    """
    # D-06: 未绑定员工（current_user.employee_id is None）
    if current_user.employee_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail='您尚未绑定员工信息，请前往「账号设置」完成绑定',
        )

    # D-06: JWT 有效但 Employee 行已被删
    employee = db.get(Employee, current_user.employee_id)
    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='员工档案缺失，请联系 HR 核对',
        )

    service = _make_service(db, settings)
    return service.get_my_tier(current_user.employee_id)
```

**明确禁止：**
- 不要加 `require_roles('admin', 'hrbp', 'manager', 'employee')` —— 降低为 `Depends(get_current_user)` 已足够（CONTEXT.md Integration Points line 212 明确约束）
- 不要接受任何 query 参数（`year`、`employee_id`、`as_of` 等全部禁止）—— ESELF-04 无参数路由红线
- 不要接受 path 参数（`/me/tier/{year}` 之类）—— 同上
- 不要在 handler 内 catch Exception —— 500 走 main.py 全局 handler
- 不要改写 `_make_service` —— 复用（虽然 get_my_tier 不走 cache，但传 cache=None 也无害）
- 不要删除其他现有 handler —— 仅修改 TODO block

**路由顺序确认：** 本 handler 放在文件**末尾**，位于 `get_available_years`（line 192-201）之后。由于本 router prefix 是 `/performance` 且现有路由都是字面量路径（`/records`、`/tier-summary`、`/recompute-tiers`、`/available-years`）——没有 `/{employee_id}` 变体 —— `/me/tier` 不会被误捕获。FastAPI 仍按声明顺序优先匹配字面量路径。
  </action>
  <verify>
    <automated>cd /Users/mac/PycharmProjects/Wage_adjust && .venv/bin/python -c "from fastapi.testclient import TestClient; from backend.app.main import create_app; app = create_app(); routes = [r.path for r in app.routes if hasattr(r, 'path')]; assert '/api/v1/performance/me/tier' in routes, f'Route not registered. Got: {[r for r in routes if \"performance\" in r]}'; print('Route /api/v1/performance/me/tier registered OK')"</automated>
  </verify>
  <acceptance_criteria>
    - `grep -n "@router.get('/me/tier', response_model=MyTierResponse)" backend/app/api/v1/performance.py` 命中 1 行
    - `grep -n "def get_my_tier(" backend/app/api/v1/performance.py` 命中 1 行（API handler）
    - `grep -n "current_user: User = Depends(get_current_user)" backend/app/api/v1/performance.py` 命中
    - `grep -n "'您尚未绑定员工信息，请前往「账号设置」完成绑定'" backend/app/api/v1/performance.py` 命中（422 中文文案精确）
    - `grep -n "'员工档案缺失，请联系 HR 核对'" backend/app/api/v1/performance.py` 命中（404 中文文案精确）
    - `grep -n "service.get_my_tier(current_user.employee_id)" backend/app/api/v1/performance.py` 命中
    - `grep -cE "TODO Phase 35|保留位（本期不实现" backend/app/api/v1/performance.py` 输出 0（原 TODO 注释已清除）
    - `grep -cE "/me/tier/\{|employee_id: str" backend/app/api/v1/performance.py` 在 `/me/tier` 附近 20 行内不得命中（无 path/query 参数，ESELF-04）
    - `grep -n "from backend.app.models.employee import Employee" backend/app/api/v1/performance.py` 命中
    - `grep -n "from backend.app.models.user import User" backend/app/api/v1/performance.py` 命中
  </acceptance_criteria>
  <done>路由已注册；TODO 注释清除；handler 实现 422/404/200 三分支；app import 无错。</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: API 层 pytest 覆盖 ≥ 5 用例</name>
  <files>backend/tests/test_api/test_performance_api.py</files>
  <read_first>
    - backend/tests/test_api/test_performance_api.py（现有 `_TestContext` 类 + `ctx` fixture + `make_user` + `auth_header` + `test_me_tier_endpoint_does_not_exist_yet` 占位，需删除）
    - backend/app/api/v1/performance.py（Task 1 新 handler）
    - .planning/phases/35-employee-self-service-experience/35-CONTEXT.md（specifics line 224）
    - backend/app/models/employee.py（建员工 fixture 时需要字段集）
  </read_first>
  <behavior>
    - 5 用例最少：happy path（绑定员工 + 有档次）+ insufficient_sample + no_snapshot + 422 未绑定 + 404 员工已删
    - 额外加 role 覆盖：admin + employee 至少各一次（证明任意角色都可调用）
  </behavior>
  <action>
在 `backend/tests/test_api/test_performance_api.py` 执行两步：

**Step A — 删除占位测试：**

删除现有文件末尾的：
```python
# ---------------------------------------------------------------------------
# Phase 35 保留位
# ---------------------------------------------------------------------------

def test_me_tier_endpoint_does_not_exist_yet(ctx):
    """GET /performance/me/tier → 404（保留位未实现）。"""
    admin = ctx.make_user(role='admin')
    client = TestClient(ctx.app)
    resp = client.get(
        '/api/v1/performance/me/tier',
        headers=ctx.auth_header(admin),
    )
    assert resp.status_code == 404
```

整块（含 section 注释）替换为 Step B 的新用例。

**Step B — 追加 ≥ 5 个新用例：**

首先在文件 imports 区确认已 import：`from backend.app.models.performance_tier_snapshot import PerformanceTierSnapshot`（已有）、`from backend.app.models.employee import Employee`（已有）。再在末尾追加：

```python
# ---------------------------------------------------------------------------
# Phase 35 ESELF-03: GET /performance/me/tier 端点测试
# ---------------------------------------------------------------------------


def _seed_snapshot_for_current_year(
    ctx,
    *,
    tiers_json: dict,
    insufficient_sample: bool = False,
    sample_size: int = 100,
) -> PerformanceTierSnapshot:
    """为 ctx 的 SQLite DB 插入一条当前年 PerformanceTierSnapshot。"""
    from datetime import datetime
    current_year = datetime.now().year
    db = ctx.db()
    try:
        snap = PerformanceTierSnapshot(
            year=current_year,
            tiers_json=tiers_json,
            sample_size=sample_size,
            insufficient_sample=insufficient_sample,
            distribution_warning=False,
            actual_distribution_json={},
            skipped_invalid_grades=0,
        )
        db.add(snap)
        db.commit()
        db.refresh(snap)
        return snap
    finally:
        db.close()


def _seed_employee_and_bind(ctx, user_creds, employee_no: str) -> str:
    """建 Employee 并绑定到 user_creds.id；返回 employee.id。"""
    from backend.app.models.user import User as UserModel
    db = ctx.db()
    try:
        emp = Employee(
            employee_no=employee_no,
            name=f'Test {employee_no}',
            department='Eng',
            job_family='Backend',
            job_level='P6',
            status='active',
        )
        db.add(emp)
        db.commit()
        db.refresh(emp)

        user = db.get(UserModel, user_creds.id)
        user.employee_id = emp.id
        db.add(user)
        db.commit()
        return emp.id
    finally:
        db.close()


def test_me_tier_happy_path_returns_tier_for_bound_employee(ctx):
    """绑定员工 + 当前年有快照 + tiers_json 命中 → 200 + tier=2。"""
    employee_user = ctx.make_user(role='employee')
    emp_id = _seed_employee_and_bind(ctx, employee_user, 'PHE35001')
    _seed_snapshot_for_current_year(
        ctx,
        tiers_json={emp_id: 2},  # str(UUID) 写入 JSON
        sample_size=120,
    )
    client = TestClient(ctx.app)
    resp = client.get(
        '/api/v1/performance/me/tier',
        headers=ctx.auth_header(employee_user),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body['tier'] == 2
    assert body['reason'] is None
    assert body['year'] is not None
    assert body['data_updated_at'] is not None


def test_me_tier_happy_path_works_for_admin_role_too(ctx):
    """任意角色只要 JWT 有效 + 有 employee_id → 200（ESELF-04 allows admin self-query）。"""
    admin_user = ctx.make_user(role='admin')
    emp_id = _seed_employee_and_bind(ctx, admin_user, 'PHE35002')
    _seed_snapshot_for_current_year(
        ctx,
        tiers_json={emp_id: 1},
        sample_size=100,
    )
    client = TestClient(ctx.app)
    resp = client.get(
        '/api/v1/performance/me/tier',
        headers=ctx.auth_header(admin_user),
    )
    assert resp.status_code == 200
    assert resp.json()['tier'] == 1


def test_me_tier_insufficient_sample_returns_reason_not_tier(ctx):
    """快照 insufficient_sample=True → 200 + tier=None + reason='insufficient_sample'。"""
    employee_user = ctx.make_user(role='employee')
    emp_id = _seed_employee_and_bind(ctx, employee_user, 'PHE35003')
    _seed_snapshot_for_current_year(
        ctx,
        tiers_json={},
        insufficient_sample=True,
        sample_size=10,
    )
    client = TestClient(ctx.app)
    resp = client.get(
        '/api/v1/performance/me/tier',
        headers=ctx.auth_header(employee_user),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body['tier'] is None
    assert body['reason'] == 'insufficient_sample'
    assert body['year'] is not None


def test_me_tier_no_snapshot_when_db_empty(ctx):
    """DB 完全无快照 → 200 + year=None + tier=None + reason='no_snapshot'。"""
    employee_user = ctx.make_user(role='employee')
    _seed_employee_and_bind(ctx, employee_user, 'PHE35004')
    # 故意不建任何 PerformanceTierSnapshot
    client = TestClient(ctx.app)
    resp = client.get(
        '/api/v1/performance/me/tier',
        headers=ctx.auth_header(employee_user),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body['year'] is None
    assert body['tier'] is None
    assert body['reason'] == 'no_snapshot'
    assert body['data_updated_at'] is None


def test_me_tier_not_ranked_when_employee_absent_from_tiers_json(ctx):
    """快照存在但 tiers_json 无该员工 → reason='not_ranked'。"""
    employee_user = ctx.make_user(role='employee')
    _seed_employee_and_bind(ctx, employee_user, 'PHE35005')
    _seed_snapshot_for_current_year(
        ctx,
        tiers_json={'some-other-uuid-not-this-user': 1},  # 故意不含本员工
        sample_size=80,
    )
    client = TestClient(ctx.app)
    resp = client.get(
        '/api/v1/performance/me/tier',
        headers=ctx.auth_header(employee_user),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body['tier'] is None
    assert body['reason'] == 'not_ranked'


def test_me_tier_returns_422_for_unbound_user(ctx):
    """current_user.employee_id is None → 422 + 中文 detail。"""
    employee_user = ctx.make_user(role='employee')
    # 不调 _seed_employee_and_bind，用户 employee_id 保持 None
    client = TestClient(ctx.app)
    resp = client.get(
        '/api/v1/performance/me/tier',
        headers=ctx.auth_header(employee_user),
    )
    assert resp.status_code == 422
    assert '您尚未绑定员工信息' in resp.text


def test_me_tier_returns_404_when_employee_deleted(ctx):
    """JWT 有效 + employee_id 非空但 Employee 行已删 → 404 + 中文 detail。"""
    from backend.app.models.user import User as UserModel
    employee_user = ctx.make_user(role='employee')
    emp_id = _seed_employee_and_bind(ctx, employee_user, 'PHE35006')
    # 直接删员工行
    db = ctx.db()
    try:
        db.query(Employee).filter(Employee.id == emp_id).delete()
        db.commit()
    finally:
        db.close()
    client = TestClient(ctx.app)
    resp = client.get(
        '/api/v1/performance/me/tier',
        headers=ctx.auth_header(employee_user),
    )
    assert resp.status_code == 404
    assert '员工档案缺失' in resp.text


def test_me_tier_response_body_contains_no_other_employee_data(ctx):
    """T-35-02 mitigation：响应体只有 4 字段，无其他员工泄露。"""
    employee_user = ctx.make_user(role='employee')
    emp_id = _seed_employee_and_bind(ctx, employee_user, 'PHE35007')
    _seed_snapshot_for_current_year(
        ctx,
        tiers_json={emp_id: 2, 'other-1': 1, 'other-2': 3},
        sample_size=200,
    )
    client = TestClient(ctx.app)
    resp = client.get(
        '/api/v1/performance/me/tier',
        headers=ctx.auth_header(employee_user),
    )
    assert resp.status_code == 200
    body = resp.json()
    # 响应体 key 严格等于 4 个契约字段
    assert set(body.keys()) == {'year', 'tier', 'reason', 'data_updated_at'}
    # other-1 / other-2 绝不能出现
    assert 'other-1' not in resp.text
    assert 'other-2' not in resp.text
    # tiers_json / sample_size 也不应出现在响应体
    assert 'tiers_json' not in resp.text
    assert 'sample_size' not in resp.text
```

**重要说明：** 如果 `_seed_employee_and_bind` 中 `Employee` 构造函数所需字段与实际 `backend/app/models/employee.py` 定义不同（如 missing `id_card_no`、`company` 等非空字段），执行时按照实际 model 补齐必填项。不要把必填字段留空导致 IntegrityError。

**禁止：**
- 不要 mock `get_current_user` —— 使用现有 `make_user` + JWT 生成（`ctx.auth_header(creds)` 模式）
- 不要写「任意调用者都获得 200」的过宽断言 —— 422/404 分支必须被精确触发
- 不要把角色覆盖塞进单个 parametrize —— 独立 test_* 函数方便定位失败
  </action>
  <verify>
    <automated>cd /Users/mac/PycharmProjects/Wage_adjust && .venv/bin/python -m pytest backend/tests/test_api/test_performance_api.py -k "me_tier" -v --no-header 2>&1 | tail -40</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "^def test_me_tier" backend/tests/test_api/test_performance_api.py` 输出 ≥ 5
    - `grep -c "test_me_tier_endpoint_does_not_exist_yet" backend/tests/test_api/test_performance_api.py` 输出 0（占位测试已删除）
    - `pytest backend/tests/test_api/test_performance_api.py -k me_tier` 退出码 0
    - `grep -n "test_me_tier_happy_path" backend/tests/test_api/test_performance_api.py` 命中
    - `grep -n "test_me_tier_returns_422_for_unbound_user" backend/tests/test_api/test_performance_api.py` 命中
    - `grep -n "test_me_tier_returns_404_when_employee_deleted" backend/tests/test_api/test_performance_api.py` 命中
    - `grep -n "test_me_tier_response_body_contains_no_other_employee_data" backend/tests/test_api/test_performance_api.py` 命中
    - `grep -n "'您尚未绑定员工信息'" backend/tests/test_api/test_performance_api.py` 命中（422 断言）
    - `grep -n "'员工档案缺失'" backend/tests/test_api/test_performance_api.py` 命中（404 断言）
  </acceptance_criteria>
  <done>≥ 5 个 me_tier 用例全部通过；占位测试已清除；覆盖 happy path (2 角色) + 3 种 reason + 422 + 404 + info leak 负向断言。</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| HTTP client → FastAPI | 外部任何能出示有效 JWT 的 actor 均可调用 `/performance/me/tier`；服务端必须保证只返回 JWT subject 本人的档次 |
| FastAPI → Service | 路由层把 `current_user.employee_id`（不是入参）作为唯一 employee 键传给 Service；无路径/查询参数可以被伪造 |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-35-02-01 | E (Privilege Escalation) / A01 Broken Access Control | GET /performance/me/tier | mitigate | 无 path / query / body 参数；`employee_id` 来源**只**是 `current_user.employee_id`（Depends(get_current_user) 由 JWT subject 决定）。Task 1 acceptance 含负向断言 `grep -cE "/me/tier/\{\|employee_id: str" = 0`。横向越权天然不可达（ESELF-04；REQUIREMENTS line 15） |
| T-35-02-02 | I (Info Disclosure) / A02 Sensitive Data Exposure | 响应体 | mitigate | `response_model=MyTierResponse` 由 FastAPI 强制字段过滤，仅 4 个契约字段（year/tier/reason/data_updated_at）可序列化；即使 Service 意外返回额外字段也被 FastAPI 裁剪。Task 2 `test_me_tier_response_body_contains_no_other_employee_data` 用例显式断言 `set(body.keys()) == {'year','tier','reason','data_updated_at'}` 且响应体不含其他员工 id / tiers_json / sample_size。符合 REQUIREMENTS line 89-103 PIPL 红线 |
| T-35-02-03 | I (Info Disclosure) | 错误态文案 | mitigate | 422 / 404 使用通用中文业务消息（「您尚未绑定员工信息」/「员工档案缺失」），不含 stack trace / SQL fragment / 其他员工数据；500 走 main.py 全局 handler 输出通用消息（不在本 handler 内 catch Exception）。Task 1 acceptance 验证精确文案串 |
| T-35-02-04 | S (Spoofing) | JWT 伪造 | transfer | JWT 校验由 `decode_token` + `User.token_version` 比对完成；本 handler 依赖 `get_current_user` 抛 401 即可，不自行实现鉴权 |
| T-35-02-05 | T (Tampering) | 响应数据篡改 | accept | HTTPS 由反向代理层保证（生产部署职责），本 handler 不额外做 MAC |
| T-35-02-06 | D (Denial of Service) | 端点刷新频率 | accept | `get_my_tier` 为单次 SELECT（最多 2 次 —— 当前年 + fallback）+ 一次 dict lookup，成本 < 10ms；无需限流 |
| T-35-02-07 | R (Repudiation) | 员工查看档次无审计 | accept | 员工查自己的档次是读路径，无业务状态变更；HR 端档次重算已有 AuditLog（Phase 34）；读路径审计非 v1.4 范围 |

**ASVS L1 checklist（本端点）：**
- V4.1.1 访问控制：每个端点显式鉴权 ✓（`Depends(get_current_user)`）
- V4.1.3 无 IDOR：无 path/query employee_id 参数 ✓
- V7.4.1 错误处理：错误不泄露敏感信息 ✓（Task 2 acceptance）
- V14.5.1 响应 schema 校验：`response_model=MyTierResponse` ✓
</threat_model>

<verification>
- `pytest backend/tests/test_api/test_performance_api.py -k me_tier` 全部通过（≥ 5 用例）
- `pytest backend/tests/test_api/test_performance_api.py` 全文件退出码 0（没有破坏 Phase 34 既有 API 测试）
- `python -c "from backend.app.main import create_app; app = create_app(); print([r.path for r in app.routes if 'me/tier' in str(getattr(r, 'path', ''))])"` 输出包含 `/api/v1/performance/me/tier`
- 所有 grep 静态断言通过（见 task acceptance_criteria）
</verification>

<success_criteria>
1. `GET /api/v1/performance/me/tier` 在 OpenAPI schema 中注册
2. handler 使用 `Depends(get_current_user)` 而非 `require_roles(...)`（任意角色可调）
3. 422 / 404 中文文案与 D-06 精确一致
4. 响应体严格 4 字段（T-35-02-02 mitigation）
5. 既有 `test_me_tier_endpoint_does_not_exist_yet` 占位测试已删除
6. ≥ 5 个新 API 用例通过，覆盖：2 角色 happy path + 3 种 reason 分支 + 422 + 404 + info leak 负向断言
</success_criteria>

<output>
After completion, create `.planning/phases/35-employee-self-service-experience/35-02-SUMMARY.md`
</output>
