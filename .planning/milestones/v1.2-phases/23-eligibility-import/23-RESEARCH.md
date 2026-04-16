# Phase 23: 调薪资格统一导入管理 - Research

**Researched:** 2026-04-12
**Domain:** 数据导入管理（Excel + 飞书多维表格）、拖拽字段映射 UI
**Confidence:** HIGH

## Summary

本阶段在现有 EligibilityManagementPage 基础上扩展 4 个数据导入 Tab（绩效等级、调薪历史、入职信息、非法定假期），每个 Tab 同时支持本地 Excel 上传和飞书多维表格同步。项目已有完备的导入基础设施（ImportService 支持 4 种类型、Celery task 异步执行、ImportResultPanel 结果展示），飞书集成也已成熟（FeishuService token 管理、分页拉取、字段映射）。

核心新增工作集中在三个方面：(1) 新建 NonStatutoryLeave 模型并扩展 ImportService 支持 `hire_info` 和 `non_statutory_leave` 两种新导入类型；(2) 在 FeishuService 中添加 RPM 限流和指数退避重试（复用 InMemoryRateLimiter 模式）；(3) 前端实现拖拽连线字段映射 UI。拖拽连线 UI 是本阶段最大技术风险点，建议使用 SVG 手绘连线 + 原生拖放 API，避免引入重量级依赖。

**Primary recommendation:** 最大化复用现有 ImportService/FeishuService 模式，拖拽映射用 SVG 连线 + HTML5 原生拖放实现，飞书限流直接复制 InMemoryRateLimiter 到 FeishuService。

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** 在现有 EligibilityManagementPage 中扩展，新增 4 个 Tab：绩效等级、调薪历史、入职信息、非法定假期。与 ImportCenter 分开，不复用 ImportCenter
- **D-02:** 每个 Tab 内同时提供"Excel 导入"和"飞书同步"两个功能区域
- **D-03:** 侧边栏菜单新增"调薪资格管理"入口，HR/admin 角色可见
- **D-04:** 手动触发同步，HR 配置字段映射后点击"开始同步"，通过 Celery task 后台执行
- **D-05:** 复用现有 FeishuConfig 的 app_id/app_secret 凭证（Settings 页面配置），每个 Tab 只需配置多维表格 URL 和字段映射
- **D-06:** 字段映射 UI 使用左右两栏拖拽连线设计（左侧飞书字段列表，右侧系统字段列表，拖拽建立连接）。不复用 FieldMappingTable 下拉选择模式
- **D-07:** HR 输入多维表格 URL 后，后端调用飞书 API 自动获取字段列表，前端展示供拖拽映射
- **D-08:** 飞书 API 限流使用固定 RPM（如 60 RPM）+ 指数退避重试。复用 LLM 服务已有的 InMemoryRateLimiter 模式
- **D-09:** 顶部 3 个统计卡片（成功/失败/跳过），下方可展开的错误明细表格。复用现有 ImportResultPanel 模式
- **D-10:** 提供"导出错误报告"按钮，下载 CSV 包含失败行号 + 原因，方便 HR 修正后重新导入
- **D-11:** 入职信息导入复用 Employee 模型的 hire_date 等字段，通过现有 ImportService 的 employees 类型处理，不新建模型
- **D-12:** 非法定假期新建 NonStatutoryLeave 模型：employee_no, year, total_days, leave_type（可选）。与 Employee 一对多关系。EligibilityEngine 已读取 max_non_statutory_leave_days 配置

### Claude's Discretion
- 拖拽连线的具体前端库选择（如 react-dnd、自研 SVG 连线等）
- Tab 内 Excel 导入和飞书同步的布局排列（上下分区还是左右分区）
- 飞书多维表格 URL 的解析方式和 app_token/table_id 提取逻辑
- NonStatutoryLeave 模型的 leave_type 枚举值定义
- 导入时数据冲突处理策略（覆盖/跳过/追加）

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ELIGIMP-01 | 提供统一的"调薪资格管理"页面，通过 Tab 切换管理 4 种数据类型的导入设置 | 现有 EligibilityManagementPage 已有 Tab 模式，扩展 TabKey 即可 |
| ELIGIMP-02 | 支持通过本地 Excel 文件导入绩效等级、调薪历史、入职信息、非法定假期数据 | ImportService 已支持前两种；hire_info 复用 employees 类型；non_statutory_leave 需新增 |
| ELIGIMP-03 | 支持通过飞书多维表格字段映射同步绩效等级、调薪历史、入职信息、非法定假期数据 | FeishuService 已有 sync_performance_records 模式，可照此扩展其他类型 |
| ELIGIMP-04 | 每种数据类型的导入结果有明确的成功/失败/跳过统计和错误明细 | ImportResultPanel + ImportErrorTable 已成熟，直接复用 |
| FEISHU-01 | FeishuService 添加请求限流（RPM 限制）和指数退避重试，防止 429 错误 | InMemoryRateLimiter 在 LlmService 已验证，移植到 FeishuService |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | 0.115.0 | API endpoints | 项目已用 [VERIFIED: requirements.txt] |
| SQLAlchemy | 2.0.36 | ORM models | 项目已用 [VERIFIED: requirements.txt] |
| Alembic | 1.14.0 | DB migration | 项目已用 [VERIFIED: requirements.txt] |
| Celery | 5.4.0 | 异步任务 | 项目已用，Phase 22 已建立 import task 模式 [VERIFIED: import_tasks.py] |
| pandas | 2.2.3 | Excel 文件读取 | 项目已用 [VERIFIED: requirements.txt] |
| openpyxl | (已安装) | xlsx 读写 | ImportService._load_table 已使用 [VERIFIED: import_service.py] |
| httpx | 0.28.1 | 飞书 API 调用 | FeishuService 已使用 [VERIFIED: feishu_service.py] |
| React | 18.3.1 | 前端框架 | 项目已用 [VERIFIED: package.json] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| HTML5 Drag & Drop API | (原生) | 拖拽交互 | 字段映射拖拽连线 |
| SVG (内联) | (原生) | 连线绘制 | 飞书字段到系统字段的可视连线 |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| 原生 HTML5 DnD + SVG | @dnd-kit (~10KB) | dnd-kit 更强大但项目无此依赖，原生足够 |
| 原生 HTML5 DnD + SVG | React Flow (@xyflow/react) | React Flow 功能过重，本场景只需简单两栏连线 |
| 原生 HTML5 DnD + SVG | react-field-mapping (npm) | 4 年未更新，风险高 |

**推荐：** 使用原生 HTML5 Drag & Drop API + SVG `<line>` 元素绘制连接线。理由：(1) 项目无拖拽库依赖，不引入新依赖更稳定；(2) 拖拽场景简单（两列列表互拖），不需要复杂嵌套或排序；(3) SVG 连线性能优秀且可控。[ASSUMED]

## Architecture Patterns

### 推荐项目结构（新增文件）
```
backend/
├── app/
│   ├── models/
│   │   └── non_statutory_leave.py      # 新模型
│   ├── services/
│   │   ├── import_service.py           # 扩展 SUPPORTED_TYPES
│   │   └── feishu_service.py           # 添加限流 + 新同步方法
│   ├── tasks/
│   │   └── feishu_sync_tasks.py        # 飞书同步 Celery task
│   ├── api/v1/
│   │   └── eligibility_import.py       # 新 API router
│   └── schemas/
│       └── eligibility_import.py       # 请求/响应 schema
frontend/
├── src/
│   ├── pages/
│   │   └── EligibilityManagementPage.tsx    # 扩展 Tab
│   ├── components/
│   │   └── eligibility-import/
│   │       ├── ImportTabContent.tsx          # 单个 Tab 内容（Excel + 飞书）
│   │       ├── FeishuFieldMapper.tsx         # 拖拽连线映射组件
│   │       ├── FeishuSyncPanel.tsx           # 飞书同步控制面板
│   │       └── ExcelImportPanel.tsx          # Excel 上传面板
│   └── services/
│       └── eligibilityImportService.ts      # API 调用
```

### Pattern 1: ImportService 扩展模式
**What:** 向 ImportService 的 SUPPORTED_TYPES 添加新类型，遵循已有的 `_import_xxx` 方法模式
**When to use:** 需要 Excel 导入新数据类型时
**Example:**
```python
# Source: backend/app/services/import_service.py (existing pattern)
SUPPORTED_TYPES = {
    'employees', 'certifications', 'performance_grades',
    'salary_adjustments', 'non_statutory_leave',  # 新增
}
REQUIRED_COLUMNS['non_statutory_leave'] = ['employee_no', 'year', 'total_days']
COLUMN_ALIASES['non_statutory_leave'] = {
    '员工工号': 'employee_no',
    '年度': 'year',
    '假期天数': 'total_days',
    '假期类型': 'leave_type',
}
```
[VERIFIED: import_service.py existing pattern]

### Pattern 2: FeishuService 通用同步方法
**What:** 在 FeishuService 中添加通用的 `sync_data_type` 方法，复用 `_fetch_all_records` + `_map_fields` 模式
**When to use:** 飞书多维表格同步新数据类型
**Example:**
```python
# Source: feishu_service.py sync_performance_records pattern
def sync_salary_adjustments(self, *, app_token, table_id, field_mapping=None) -> dict:
    if field_mapping is None:
        field_mapping = {'员工工号': 'employee_no', '调薪日期': 'adjustment_date', ...}
    config = self.get_config()
    token = self._ensure_token(config.app_id, app_secret)
    records = self._fetch_all_records(token, app_token, table_id, field_mapping)
    # ... upsert logic matching import_service pattern
```
[VERIFIED: feishu_service.py sync_performance_records]

### Pattern 3: Celery Task 包装
**What:** 用 Celery task 包装耗时同步操作，前端通过 useTaskPolling 轮询进度
**When to use:** 飞书同步任务（可能涉及大量 API 调用和数据写入）
**Example:**
```python
# Source: backend/app/tasks/import_tasks.py
@celery_app.task(name='tasks.feishu_sync_eligibility', bind=True, ...)
def feishu_sync_task(self, sync_type, app_token, table_id, field_mapping, operator_id=None):
    self.update_state(state='PROGRESS', meta={'processed': 0, 'total': 0, ...})
    # ... 调用 FeishuService 执行同步
```
[VERIFIED: import_tasks.py existing pattern]

### Pattern 4: 飞书多维表格 URL 解析
**What:** 从飞书多维表格 URL 中提取 app_token 和 table_id
**When to use:** HR 输入多维表格 URL 时自动解析
**Example:**
```python
# 飞书多维表格 URL 格式：
# https://xxx.feishu.cn/base/BascXXXXXXXX?table=tblYYYYYYYY
# 或 https://xxx.feishu.cn/base/BascXXXXXXXX/tblYYYYYYYY
import re

def parse_bitable_url(url: str) -> tuple[str, str]:
    """从飞书多维表格 URL 中提取 app_token 和 table_id。"""
    # Pattern 1: /base/{app_token}?table={table_id}
    match = re.search(r'/base/([A-Za-z0-9]+)\?.*table=([A-Za-z0-9]+)', url)
    if match:
        return match.group(1), match.group(2)
    # Pattern 2: /base/{app_token}/{table_id}
    match = re.search(r'/base/([A-Za-z0-9]+)/([A-Za-z0-9]+)', url)
    if match:
        return match.group(1), match.group(2)
    raise ValueError('无法解析飞书多维表格 URL，请检查格式')
```
[ASSUMED - 基于飞书 URL 结构推断，需测试验证]

### Anti-Patterns to Avoid
- **不要在每个 Tab 创建独立的 FeishuConfig 记录：** 决策 D-05 明确凭证复用全局 FeishuConfig，每个 Tab 只需 app_token + table_id + field_mapping
- **不要在前端直接调用飞书 API：** 所有飞书 API 调用必须通过后端转发，确保凭证安全
- **不要跳过 employee_no 匹配验证：** 所有导入/同步都必须先验证 employee_no 存在于 Employee 表中

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| RPM 限流 | 自己写时间窗口算法 | 复制 InMemoryRateLimiter | 已验证模式，含滑动窗口和等待逻辑 |
| Excel 文件解析 | 自己读 cell | pandas.read_excel + openpyxl | 已有完整的编码检测和格式处理 |
| 文件导入错误处理 | 自己写 try/catch 逻辑 | ImportService 的 SAVEPOINT + per-row 错误模式 | 数据库事务安全、局部失败不影响整体 |
| 导入结果展示 | 重建统计卡片和错误表格 | ImportResultPanel + ImportErrorTable | 已成熟的组件，风格一致 |
| Celery task 进度上报 | 自己写状态轮询 | update_state(PROGRESS) + useTaskPolling | Phase 22 已验证的模式 |
| 飞书 token 管理 | 自己写过期刷新 | FeishuService._ensure_token | 含提前 5 分钟刷新缓冲 |

**Key insight:** 本阶段 90% 以上的后端逻辑可以复用已有模式，只需扩展数据类型和配置。最大创新点是前端拖拽连线 UI。

## Common Pitfalls

### Pitfall 1: 飞书 API 429 Too Many Requests
**What goes wrong:** 短时间内发送过多请求导致飞书 API 返回 429 错误
**Why it happens:** 分页拉取大量数据时，每页请求间隔不足
**How to avoid:** 在 FeishuService 的 `_fetch_all_records` 中集成 InMemoryRateLimiter，每次请求前 `acquire()`
**Warning signs:** 飞书 API 返回 code=99991400 或 HTTP 429

### Pitfall 2: hire_info 导入与 employees 类型冲突
**What goes wrong:** D-11 说 hire_info 复用 employees 类型，但实际只需更新 hire_date 字段
**Why it happens:** employees 类型要求 employee_no + name + department 全部必填
**How to avoid:** 在 ImportService 中为 hire_info 创建单独的 `_import_hire_info` 方法，只要求 employee_no + hire_date，查找现有 Employee 记录并更新 hire_date
**Warning signs:** HR 导入入职信息时被要求填写所有员工基础字段

### Pitfall 3: 飞书字段类型不一致
**What goes wrong:** 飞书多维表格中的日期/数字字段可能以文本、时间戳、数组等多种格式返回
**Why it happens:** 飞书字段类型复杂（文本、数字、日期、单选、多选等），返回格式不统一
**How to avoid:** 复用 FeishuService._extract_cell_value 方法，并在每种同步方法中添加类型强制转换
**Warning signs:** 同步后数据为空或格式错误

### Pitfall 4: SVG 连线定位不准
**What goes wrong:** 拖拽连线后，SVG 线段位置与实际元素不对齐
**Why it happens:** SVG 坐标系与 DOM 元素位置使用不同参考系
**How to avoid:** 使用 `getBoundingClientRect()` 获取元素位置，相对于 SVG 容器计算偏移量，并在窗口 resize 时重新计算
**Warning signs:** 连线偏移或断裂

### Pitfall 5: NonStatutoryLeave 与 EligibilityEngine 集成遗漏
**What goes wrong:** 导入了非法定假期数据，但 EligibilityEngine 仍读不到
**Why it happens:** EligibilityEngine 目前是纯计算引擎，不访问 DB；数据需要在调用层查询后传入
**How to avoid:** 确保 EligibilityService 查询 NonStatutoryLeave 记录并传入 EligibilityEngine
**Warning signs:** 资格评估中假期规则始终显示 data_missing

### Pitfall 6: 多维表格 URL 中 app_token 与 table_id 格式变化
**What goes wrong:** 飞书不同版本或不同客户端生成的 URL 格式可能不同
**Why it happens:** 飞书产品迭代可能更改 URL 结构
**How to avoid:** URL 解析添加多种正则匹配模式，并在解析失败时提供清晰的用户提示
**Warning signs:** HR 粘贴 URL 后系统报错"无法解析"

## Code Examples

### 飞书多维表格字段列表 API 调用
```python
# Source: https://open.feishu.cn/document/server-docs/docs/bitable-v1/app-table-field/list
# [CITED: open.feishu.cn/document/server-docs/docs/bitable-v1/app-table-field/list]
def list_bitable_fields(self, token: str, app_token: str, table_id: str) -> list[dict]:
    """获取飞书多维表格的字段列表，供前端映射使用。"""
    url = f'{self.FEISHU_BASE_URL}/bitable/v1/apps/{app_token}/tables/{table_id}/fields'
    headers = {'Authorization': f'Bearer {token}'}
    all_fields: list[dict] = []
    page_token: str | None = None
    
    while True:
        params: dict = {'page_size': 100}
        if page_token:
            params['page_token'] = page_token
        resp = httpx.get(url, headers=headers, params=params, timeout=10)
        data = resp.json()
        if data.get('code') != 0:
            raise RuntimeError(f'获取字段列表失败: {data.get("msg")}')
        items = data.get('data', {}).get('items', [])
        for item in items:
            all_fields.append({
                'field_id': item['field_id'],
                'field_name': item['field_name'],
                'type': item.get('type'),
                'ui_type': item.get('ui_type'),
            })
        if not data.get('data', {}).get('has_more'):
            break
        page_token = data['data']['page_token']
    
    return all_fields
```

### InMemoryRateLimiter 移植到 FeishuService
```python
# Source: backend/app/services/llm_service.py InMemoryRateLimiter
# [VERIFIED: llm_service.py line 73-88]
# 在 FeishuService.__init__ 中初始化:
self._rate_limiter = InMemoryRateLimiter(60)  # 60 RPM

# 在 _fetch_all_records 的每次请求前:
self._rate_limiter.acquire()  # 阻塞直到可用
resp = httpx.post(url, headers=headers, json=body, timeout=30)
```

### NonStatutoryLeave 模型
```python
# Source: 遵循 PerformanceRecord / SalaryAdjustmentRecord 模式
# [VERIFIED: performance_record.py, salary_adjustment_record.py]
class NonStatutoryLeave(UUIDPrimaryKeyMixin, CreatedAtMixin, UpdatedAtMixin, Base):
    __tablename__ = 'non_statutory_leaves'
    __table_args__ = (
        UniqueConstraint('employee_id', 'year', name='uq_leave_employee_year'),
    )
    employee_id: Mapped[str] = mapped_column(String(36), ForeignKey('employees.id'), nullable=False, index=True)
    employee_no: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    total_days: Mapped[float] = mapped_column(Numeric(6, 1), nullable=False)
    leave_type: Mapped[str | None] = mapped_column(String(32), nullable=True, comment='事假/病假/其他')
    source: Mapped[str] = mapped_column(String(32), nullable=False, default='manual')
```

### 前端拖拽连线 UI 核心逻辑
```typescript
// Source: HTML5 Drag & Drop API + SVG
// [ASSUMED - 基于原生 Web API]
interface FieldConnection {
  feishuField: string;
  systemField: string;
}

// 左侧飞书字段项设置 draggable
// 右侧系统字段项设置 onDragOver + onDrop
// 建立连接后，计算两个元素的 getBoundingClientRect()
// 在覆盖层 SVG 中绘制 <line> 或 <path> 连接

function renderConnections(
  connections: FieldConnection[],
  containerRef: React.RefObject<HTMLDivElement>,
) {
  return (
    <svg className="absolute inset-0 pointer-events-none" style={{ zIndex: 1 }}>
      {connections.map((conn, i) => {
        const left = document.getElementById(`feishu-${conn.feishuField}`);
        const right = document.getElementById(`system-${conn.systemField}`);
        if (!left || !right || !containerRef.current) return null;
        const containerRect = containerRef.current.getBoundingClientRect();
        const leftRect = left.getBoundingClientRect();
        const rightRect = right.getBoundingClientRect();
        return (
          <line
            key={i}
            x1={leftRect.right - containerRect.left}
            y1={leftRect.top + leftRect.height / 2 - containerRect.top}
            x2={rightRect.left - containerRect.left}
            y2={rightRect.top + rightRect.height / 2 - containerRect.top}
            stroke="var(--color-primary)"
            strokeWidth={2}
          />
        );
      })}
    </svg>
  );
}
```

## 飞书 API 集成细节

### List Fields API
- **端点:** `GET /open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/fields` [CITED: open.feishu.cn/document/server-docs/docs/bitable-v1/app-table-field/list]
- **限流:** 20 请求/秒（飞书官方限制）
- **分页:** page_size 最大 100，通过 page_token 翻页
- **响应:** 返回 field_id, field_name, type, ui_type, is_primary 等字段信息
- **所需权限:** `base:field:read` 或 `bitable:app:readonly`

### RPM 限流实现方案
FeishuService 当前 `_fetch_all_records` 方法在循环中发送请求但无限流。需要在每次 `httpx.post` 之前调用限流器的 `acquire()` 方法。飞书官方限制是 20 req/s，但决策 D-08 建议使用 60 RPM（1 req/s）作为安全上限。

建议方案：
1. 从 `llm_service.py` 提取 `InMemoryRateLimiter` 到 `backend/app/core/rate_limiter.py` 作为共享工具
2. FeishuService 在 `__init__` 中初始化限流器
3. `_fetch_all_records` 和 `list_bitable_fields` 中每次请求前调用 `acquire()`
4. 指数退避重试：在 429 响应时等待 `base_delay * 2^attempt` 秒后重试

## Tab 内布局推荐

**推荐上下分区布局：** [ASSUMED]
```
┌──────────────────────────────────────┐
│ Tab: 绩效等级 | 调薪历史 | 入职信息 | 非法定假期 │
├──────────────────────────────────────┤
│ [Excel 导入区]                        │
│ ┌ 文件上传区域 ─────────────────┐    │
│ │ 拖拽文件到此处或点击上传       │    │
│ └─────────────────────────────┘    │
│ [下载模板] [开始导入]                 │
├──────────────────────────────────────┤
│ [飞书同步区]                          │
│ 多维表格 URL: [____________] [获取字段] │
│ ┌ 字段映射（拖拽连线）──────────┐    │
│ │ 飞书字段  ←──→  系统字段      │    │
│ └─────────────────────────────┘    │
│ [开始同步]                            │
├──────────────────────────────────────┤
│ [导入结果] (ImportResultPanel)         │
│ 成功: 120 | 失败: 3 | 跳过: 5        │
│ [展开错误明细] [导出错误报告]           │
└──────────────────────────────────────┘
```

理由：上下分区更自然地表达操作流程（先选择来源，再查看结果），且不需要响应式适配。

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| FieldMappingTable 下拉选择 | 拖拽连线映射 | Phase 23 (D-06) | 用户体验提升，更直观 |
| 飞书同步无限流 | InMemoryRateLimiter | Phase 23 (FEISHU-01) | 防止 429 错误 |
| 手动输入飞书字段名 | 自动获取字段列表 | Phase 23 (D-07) | 减少配置错误 |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | 原生 HTML5 DnD + SVG 足以实现拖拽连线需求 | Standard Stack | 若不够需引入 @dnd-kit，增加 ~10KB 依赖 |
| A2 | 飞书多维表格 URL 格式为 /base/{app_token}?table={table_id} 或 /base/{app_token}/{table_id} | Architecture Patterns | URL 解析失败导致功能不可用，需实际测试 |
| A3 | NonStatutoryLeave 的 leave_type 使用 '事假'/'病假'/'其他' 枚举 | Code Examples | 若 HR 有其他分类需扩展 |
| A4 | Tab 内上下分区布局优于左右分区 | Tab 布局推荐 | 纯 UX 偏好，可调整 |
| A5 | hire_info 导入只需更新 Employee.hire_date 而非创建/更新完整记录 | Pitfalls | 若 HR 期望同时更新其他字段则需扩展 |

## Open Questions

1. **飞书多维表格 URL 的实际格式范围**
   - What we know: 常见格式包含 /base/{app_token}?table={table_id}
   - What's unclear: 是否有更多 URL 变体（如不同地区的飞书域名）
   - Recommendation: 实现时支持多种正则模式，失败时提示用户手动输入 app_token 和 table_id

2. **非法定假期的 leave_type 枚举值**
   - What we know: D-12 标注 leave_type 为可选字段
   - What's unclear: 业务方需要哪些具体类型分类
   - Recommendation: 使用自由文本字段（String(32)），不强制枚举，让 HR 自定义

3. **入职信息导入的精确字段范围**
   - What we know: D-11 说复用 Employee 模型的 hire_date 等字段
   - What's unclear: "等字段"还包括什么（entry_type? probation_end_date?）
   - Recommendation: 最小实现只导入 employee_no + hire_date，后续按需扩展

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.3.5 |
| Config file | 无独立 pytest.ini，使用默认配置 |
| Quick run command | `python -m pytest backend/tests/test_services/test_import_service.py -x -q` |
| Full suite command | `python -m pytest backend/tests/ -x -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ELIGIMP-01 | 4 Tab 页面可渲染 | manual | 浏览器验证 | N/A |
| ELIGIMP-02 | non_statutory_leave Excel 导入 | unit | `pytest backend/tests/test_services/test_import_service.py -x -k non_statutory` | Wave 0 |
| ELIGIMP-02 | hire_info Excel 导入 | unit | `pytest backend/tests/test_services/test_import_service.py -x -k hire_info` | Wave 0 |
| ELIGIMP-03 | 飞书同步 salary_adjustments | unit | `pytest backend/tests/test_services/test_feishu_sync.py -x` | Wave 0 |
| ELIGIMP-04 | 导入结果统计正确 | unit | 复用现有 test_import_service.py 模式 | 已有部分 |
| FEISHU-01 | 限流器阻止超 RPM 请求 | unit | `pytest backend/tests/test_services/test_rate_limiter.py -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest backend/tests/test_services/test_import_service.py -x -q`
- **Per wave merge:** `python -m pytest backend/tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/test_services/test_feishu_sync.py` -- 飞书同步新类型测试
- [ ] `backend/tests/test_services/test_rate_limiter.py` -- InMemoryRateLimiter 独立测试
- [ ] `backend/tests/test_models/test_non_statutory_leave.py` -- 新模型基础测试

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | JWT + require_roles('admin', 'hrbp') 已有 |
| V3 Session Management | no | 已有 |
| V4 Access Control | yes | require_roles 依赖注入 |
| V5 Input Validation | yes | Pydantic schema + per-row 校验 |
| V6 Cryptography | yes | 飞书 app_secret 使用 AES-256-GCM 加密存储 |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| 飞书凭证泄露 | Information Disclosure | app_secret 加密存储，API 返回 masked |
| 恶意 Excel 文件 | Tampering | MAX_ROWS 限制、pandas 安全读取 |
| 飞书 URL 注入 | Spoofing | 正则验证 URL 格式，只接受 feishu.cn 域名 |
| 批量导入拒绝服务 | Denial of Service | MAX_ROWS=5000 限制、Celery task 超时 |

## Sources

### Primary (HIGH confidence)
- `backend/app/services/import_service.py` -- ImportService 完整模式和 SUPPORTED_TYPES
- `backend/app/services/feishu_service.py` -- FeishuService token 管理、分页拉取、字段映射
- `backend/app/tasks/import_tasks.py` -- Celery task 模式
- `backend/app/services/llm_service.py` -- InMemoryRateLimiter 实现
- `backend/app/models/performance_record.py` -- 模型结构参考
- `frontend/src/pages/EligibilityManagementPage.tsx` -- 现有 Tab 页面结构
- `frontend/src/components/import/ImportResultPanel.tsx` -- 导入结果组件
- `frontend/src/hooks/useTaskPolling.ts` -- Celery task 轮询 hook

### Secondary (MEDIUM confidence)
- [飞书 List Fields API](https://open.feishu.cn/document/server-docs/docs/bitable-v1/app-table-field/list) -- 字段列表端点、参数、响应结构
- [飞书 Bitable Overview](https://open.feishu.cn/document/server-docs/docs/bitable-v1/bitable-overview) -- 多维表格 API 概览

### Tertiary (LOW confidence)
- 飞书多维表格 URL 格式 -- 基于常见观察，未找到官方规范文档

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- 全部复用已有依赖，无新依赖
- Architecture: HIGH -- 严格遵循项目现有模式
- Pitfalls: MEDIUM -- 飞书 API 行为和 URL 格式基于部分观察
- 拖拽连线 UI: MEDIUM -- 原生 API 方案可行但需实际测试体验

**Research date:** 2026-04-12
**Valid until:** 2026-05-12 (30 days - 模式稳定)
