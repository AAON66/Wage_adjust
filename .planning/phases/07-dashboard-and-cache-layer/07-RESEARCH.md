# Phase 7: 看板与缓存层 - 研究报告

**研究日期:** 2026-03-28
**领域:** ECharts 可视化 + Redis 缓存 + SQLAlchemy 聚合查询 + 看板架构
**总体置信度:** HIGH

## 摘要

Phase 7 需要将现有看板从全表扫描 + 纯 CSS 图表改造为 SQL 聚合查询 + Redis 缓存 + ECharts 可视化的现代看板架构。现有代码库中 `DashboardService` 已有完整的数据聚合逻辑（7 个方法），但全部基于 Python 内存循环遍历——需要逐个改造为 SQL 侧 `GROUP BY` 聚合。前端已有 6 个看板组件（`DistributionChart`、`HeatmapChart`、`OverviewCards` 等），其中 `DistributionChart` 和 `HeatmapChart` 为纯 CSS 实现，需整体替换为 ECharts。

Redis 在项目中已有使用先例（`rate_limit.py` 中的限流器和 `llm_service.py` 中的 Redis 限流器），`requirements.txt` 已包含 `redis==5.2.1` 和 `hiredis==3.1.0`，`config.py` 已有 `redis_url` 配置。缓存层需新增一个通用的 Redis 缓存服务，为看板 API 提供按 `cycle_id + role` 隔离的缓存。

**核心建议:** 分三波推进——(1) 后端 SQL 聚合 + Redis 缓存层 (2) 前端 ECharts 替换全部图表 + 新增审批流水线图和调薪直方图 (3) 部门下钻 + KPI 实时刷新。

<user_constraints>
## 用户约束 (来自 CONTEXT.md)

### 锁定决策
- **D-01:** 使用 **ECharts** 作为图表库。安装 `echarts` + `echarts-for-react`。
- **D-02:** **全部替换**现有纯 CSS 图表组件（DistributionChart、HeatmapChart 等）为 ECharts 实现。统一技术栈，不保留混合风格。
- **D-03:** Redis 为**必须依赖**，开发环境也使用 Redis。不提供内存缓存回退。
- **D-04:** 缓存 key 包含 `cycle_id` + 用户角色，防止跨角色数据泄漏。TTL 按图表类型 5-15 分钟。
- **D-05:** 要保证后续部署上服务器的方便程度。本阶段确保 Redis 配置清晰，但 Docker 一键部署延后。
- **D-06:** 部门下钻使用**页内展开**方式。点击部门行后在当前页面下方展开该部门的等级分布和调薪平均值图表。不弹出模态框，不跳转新页面。
- **D-07:** KPI 卡片展示 4 个指标：待审批数（实时 30 秒刷新）、员工总数/已评估数、平均调薪幅度、AI 等级分布概览。
- **D-08:** 待审批数每 30 秒轮询刷新（`setInterval`），不需要 WebSocket。其他图表使用 Redis TTL 自然过期刷新。
- **D-09:** 看板页面使用**双列网格**布局。KPI 卡片横排顶部，下方图表双列排列（AI等级分布 | 调薪幅度分布），审批流水线和部门表格占满宽。
- **D-10:** 顶部包含**周期选择器**下拉框，切换周期后所有图表刷新。默认显示最新周期。
- **D-11:** 看板仅对 **admin/hrbp/manager** 可见。员工角色不显示看板入口。
- **D-12:** manager 只能看到自己管理的部门数据，admin/hrbp 看全量。沿用已有 AccessScopeService 权限模型。

### Claude 自由裁量
- ECharts 主题色和图表样式细节
- SQL 聚合查询的具体写法
- Redis key 命名规范和过期策略细节
- KPI 卡片的具体视觉样式

### 延后事项 (范围外)
- **Docker 一键部署** — 用户明确要求延后到单独阶段
- **员工自助看板** — 员工角色不可见看板
- **看板数据导出** — 导出 PDF/Excel 功能不在当前范围
</user_constraints>

<phase_requirements>
## 阶段需求

| ID | 描述 | 研究支持 |
|----|------|---------|
| DASH-01 | SQL 侧聚合替换全表扫描 | SQLAlchemy `func.count`/`func.avg`/`func.sum` + `GROUP BY` 模式，见架构模式章节 |
| DASH-02 | Redis 缓存 + TTL + 角色隔离 | 项目已有 `redis==5.2.1`，新增 `CacheService` 封装，key 格式 `dashboard:{cycle_id}:{role}:{chart_type}` |
| DASH-03 | AI 等级分布图表 | ECharts 饼图/柱状图，数据从 `ai_evaluations` 表 GROUP BY `ai_level` |
| DASH-04 | 调薪幅度分布直方图 | ECharts 柱状图，数据从 `salary_recommendations` 表按区间聚合 |
| DASH-05 | 审批流水线状态图 | ECharts 柱状图/漏斗图，数据从 `approval_records` + `salary_recommendations` 聚合各状态计数 |
| DASH-06 | 部门下钻 | 页内展开模式，复用 `DepartmentInsightTable`，展开行内加载部门级 ECharts 图表 |
| DASH-07 | KPI 实时刷新 | 待审批数 30 秒 `setInterval` 轮询独立 API，其他走 Redis TTL |
</phase_requirements>

## 标准技术栈

### 核心

| 库 | 版本 | 用途 | 为何标准 |
|----|------|------|---------|
| echarts | 6.0.0 | 图表渲染引擎 | Apache 开源，功能丰富，中文支持好 |
| echarts-for-react | 3.0.6 | React 封装组件 | 官方推荐的 React 包装，TypeScript 支持完整 |
| redis (Python) | 5.2.1 | Redis 客户端 | 项目已依赖，requirements.txt 已声明 |
| hiredis | 3.1.0 | Redis 高性能解析器 | 项目已依赖，提升 redis-py 性能 |

### 支撑

| 库 | 版本 | 用途 | 使用场景 |
|----|------|------|---------|
| SQLAlchemy func | 2.0.36 | SQL 聚合函数 | `func.count`、`func.avg`、`func.sum` 用于看板查询 |

### 替代方案对比

| 标准选择 | 可替代 | 权衡 |
|----------|--------|------|
| echarts-for-react | 直接用 echarts + useRef | echarts-for-react 提供声明式 API，减少手动管理 |
| 手写 Redis 缓存层 | fastapi-cache 库 | 项目需要按角色隔离 key，手写更可控 |

**安装命令:**

```bash
# 前端
cd frontend && npm install echarts@6.0.0 echarts-for-react@3.0.6

# 后端 (redis 已在 requirements.txt)
# 无需额外安装
```

## 架构模式

### 推荐目录结构变更

```
backend/app/
├── services/
│   ├── dashboard_service.py    # 改造: 全表扫描 -> SQL 聚合
│   └── cache_service.py        # 新增: Redis 缓存封装
├── api/v1/
│   └── dashboard.py            # 改造: 添加缓存调用 + 新端点
└── schemas/
    └── dashboard.py            # 改造: 新增审批流水线、调薪分布 schema

frontend/src/
├── components/dashboard/
│   ├── AILevelChart.tsx         # 新增: ECharts 柱状图/饼图替代 DistributionChart
│   ├── SalaryDistChart.tsx      # 新增: ECharts 调薪幅度直方图
│   ├── ApprovalPipelineChart.tsx # 新增: ECharts 审批流水线状态图
│   ├── DepartmentDrilldown.tsx  # 新增: 部门下钻展开组件
│   ├── KpiCards.tsx             # 新增: 替代 OverviewCards，含 30 秒轮询
│   ├── DepartmentInsightTable.tsx # 改造: 添加行展开下钻
│   ├── DistributionChart.tsx    # 删除: 被 ECharts 替代
│   └── HeatmapChart.tsx         # 删除: 被 ECharts 替代
├── hooks/
│   └── usePolling.ts            # 新增: 可复用的轮询 hook
└── pages/
    └── Dashboard.tsx            # 改造: 双列布局 + 新组件 + 周期选择器
```

### 模式 1: SQL 聚合替换全表扫描

**问题:** 现有 `DashboardService._evaluations()` 加载所有评估记录到内存，再用 Python Counter/循环聚合。
**方案:** 使用 SQLAlchemy `func` 在数据库侧完成聚合。

```python
# 示例: AI 等级分布聚合查询
from sqlalchemy import func, select, case

def get_ai_level_distribution_sql(self, cycle_id: str | None, department_filter: set[str] | None) -> list[dict]:
    query = (
        select(
            AIEvaluation.ai_level,
            func.count(AIEvaluation.id).label('count'),
        )
        .join(AIEvaluation.submission)
        .join(EmployeeSubmission.employee)
    )
    if cycle_id:
        query = query.where(EmployeeSubmission.cycle_id == cycle_id)
    if department_filter is not None:
        query = query.where(Employee.department.in_(department_filter))
    query = query.group_by(AIEvaluation.ai_level)
    rows = self.db.execute(query).all()
    return [{'label': row.ai_level, 'value': row.count} for row in rows]
```

**要点:** 权限过滤需要在 SQL 查询中通过 `WHERE Employee.department IN (...)` 实现，而非加载后在 Python 中过滤。admin/hrbp 不加部门过滤，manager 只过滤自己管理的部门。

### 模式 2: Redis 缓存服务

**设计:** 通用的 Redis 缓存封装，支持按 key 存取 JSON，自动序列化/反序列化。

```python
# backend/app/services/cache_service.py
import json
import redis

class CacheService:
    KEY_PREFIX = 'dashboard'

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    def _build_key(self, chart_type: str, cycle_id: str | None, role: str) -> str:
        cycle_part = cycle_id or 'all'
        return f'{self.KEY_PREFIX}:{cycle_part}:{role}:{chart_type}'

    def get(self, chart_type: str, cycle_id: str | None, role: str) -> dict | list | None:
        key = self._build_key(chart_type, cycle_id, role)
        raw = self.redis.get(key)
        if raw is None:
            return None
        return json.loads(raw)

    def set(self, chart_type: str, cycle_id: str | None, role: str, data: dict | list, ttl_seconds: int = 300) -> None:
        key = self._build_key(chart_type, cycle_id, role)
        self.redis.setex(key, ttl_seconds, json.dumps(data, default=str))

    def invalidate_cycle(self, cycle_id: str) -> None:
        pattern = f'{self.KEY_PREFIX}:{cycle_id}:*'
        keys = self.redis.keys(pattern)
        if keys:
            self.redis.delete(*keys)
```

**TTL 策略:**
- KPI 待审批数: 不缓存（实时查询 + 30 秒前端轮询）
- AI 等级分布: 10 分钟
- 调薪幅度分布: 10 分钟
- 审批流水线: 5 分钟（变化频繁）
- 部门洞察: 15 分钟
- 部门下钻: 10 分钟

### 模式 3: ECharts 组件封装

**设计:** 每个图表一个组件，接收数据 props，内部构建 ECharts option。

```typescript
// 示例: AI 等级分布柱状图
import ReactECharts from 'echarts-for-react';
import type { EChartsOption } from 'echarts';

interface AILevelChartProps {
  data: { label: string; value: number }[];
}

const LEVEL_LABELS: Record<string, string> = {
  'Level 1': 'AI 一级', 'Level 2': 'AI 二级', 'Level 3': 'AI 三级',
  'Level 4': 'AI 四级', 'Level 5': 'AI 五级',
};

export function AILevelChart({ data }: AILevelChartProps) {
  const option: EChartsOption = {
    tooltip: { trigger: 'axis' },
    xAxis: {
      type: 'category',
      data: data.map(d => LEVEL_LABELS[d.label] ?? d.label),
    },
    yAxis: { type: 'value', name: '人数' },
    series: [{
      type: 'bar',
      data: data.map(d => d.value),
      itemStyle: { borderRadius: [4, 4, 0, 0] },
    }],
  };
  return <ReactECharts option={option} style={{ height: 300 }} />;
}
```

### 模式 4: 部门下钻 (页内展开)

**设计:** `DepartmentInsightTable` 每行增加展开按钮，点击后异步加载该部门的详细数据。

```typescript
// 状态管理
const [expandedDept, setExpandedDept] = useState<string | null>(null);
const [drilldownData, setDrilldownData] = useState<DeptDrilldownData | null>(null);

// 点击行时
async function handleExpand(department: string) {
  if (expandedDept === department) {
    setExpandedDept(null);
    return;
  }
  setExpandedDept(department);
  const data = await fetchDepartmentDrilldown(cycleId, department);
  setDrilldownData(data);
}

// 渲染: 在表格行后面条件渲染展开面板
{expandedDept === row.department && drilldownData && (
  <DepartmentDrilldown data={drilldownData} />
)}
```

### 模式 5: KPI 卡片 30 秒轮询

```typescript
// hooks/usePolling.ts
export function usePolling<T>(fetcher: () => Promise<T>, intervalMs: number) {
  const [data, setData] = useState<T | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function poll() {
      try {
        const result = await fetcher();
        if (!cancelled) setData(result);
      } catch { /* 静默失败，下次重试 */ }
    }
    void poll(); // 立即执行一次
    const id = setInterval(poll, intervalMs);
    return () => { cancelled = true; clearInterval(id); };
  }, [fetcher, intervalMs]);

  return data;
}
```

### 反模式

- **反模式: 缓存不含角色标识** — 会导致 manager 看到 admin 的全量数据。缓存 key 必须包含角色。
- **反模式: 前端轮询所有图表** — 只有待审批数需要 30 秒轮询，其他图表依赖后端 Redis TTL 自然过期。
- **反模式: 在 Python 中做聚合后再缓存** — 仍然是全表扫描，只是减少了频率。应先改 SQL 聚合再加缓存。
- **反模式: `KEYS` 命令在生产环境** — `KEYS *` 是 O(N) 操作，生产环境应改用 `SCAN`。但本项目 key 数量很少（几十个），可以暂时接受。

## 不要自己造轮子

| 问题 | 不要手写 | 使用 | 原因 |
|------|---------|------|------|
| 图表渲染 | Canvas/SVG 手绘 | echarts + echarts-for-react | 交互、动画、响应式全内置 |
| 图表响应式 | 手动监听 resize | echarts-for-react 的 autoResize | 组件内置自动 resize |
| JSON 序列化 | 自定义编码器 | `json.dumps(data, default=str)` | Decimal/datetime 安全序列化 |

## 常见陷阱

### 陷阱 1: SQLAlchemy 聚合查询的权限过滤

**问题:** 现有 `_is_accessible` 方法在 Python 侧逐条过滤。改为 SQL 聚合后，权限必须在 SQL WHERE 子句中实现。
**根因:** `GROUP BY` 查询无法在结果集上再做 Python 过滤。
**预防:** 在 SQL 查询中根据用户角色添加 `WHERE Employee.department IN (...)` 条件。admin/hrbp 不加条件，manager 过滤部门。
**发现信号:** 聚合结果中 manager 能看到非自己部门的数据。

### 陷阱 2: Redis 连接管理

**问题:** 每次请求创建新 Redis 连接会导致连接泄漏。
**根因:** Redis 连接未复用。
**预防:** 在 app 启动时创建 `redis.Redis` 连接池（`redis.from_url(url)` 默认使用连接池），通过 FastAPI 依赖注入共享。
**发现信号:** Redis `CLIENT LIST` 中连接数不断增长。

### 陷阱 3: ECharts 组件内存泄漏

**问题:** ECharts 实例未在组件卸载时销毁。
**根因:** 忘记调用 `dispose()`。
**预防:** `echarts-for-react` 的 `ReactECharts` 组件内部已自动处理 dispose，无需手动管理。但如果直接使用 `echarts.init()`，必须在 `useEffect` 清理函数中 `dispose()`。
**发现信号:** 浏览器内存持续增长。

### 陷阱 4: 缓存穿透 (Cache Stampede)

**问题:** 多个并发请求同时发现缓存过期，全部去查数据库。
**根因:** 无锁机制。
**预防:** 对于本项目规模（内部工具，并发低），TTL 过期后自然刷新即可，无需加锁。如果未来并发增大，可加 Redis 分布式锁。
**发现信号:** TTL 过期瞬间数据库负载飙升。

### 陷阱 5: Decimal 序列化

**问题:** `json.dumps()` 无法序列化 `Decimal` 类型。
**根因:** JSON 标准不支持 Decimal。
**预防:** 使用 `json.dumps(data, default=str)` 或在聚合查询中转换为 float。
**发现信号:** `TypeError: Object of type Decimal is not JSON serializable`。

### 陷阱 6: 前端轮询在页面切换后仍运行

**问题:** `setInterval` 在组件卸载后继续执行。
**根因:** 未清理定时器。
**预防:** 在 `useEffect` 清理函数中 `clearInterval`。
**发现信号:** 控制台报 "Can't perform a React state update on an unmounted component"。

## 代码示例

### 调薪幅度分布 SQL 聚合

```python
from sqlalchemy import func, case, select

def get_salary_distribution_sql(self, cycle_id: str | None, department_filter: set[str] | None) -> list[dict]:
    ratio = SalaryRecommendation.final_adjustment_ratio
    bucket = case(
        (ratio < 0.05, '0-5%'),
        (ratio < 0.10, '5-10%'),
        (ratio < 0.15, '10-15%'),
        (ratio < 0.20, '15-20%'),
        else_='20%+',
    ).label('bucket')

    query = (
        select(bucket, func.count().label('count'))
        .join(SalaryRecommendation.evaluation)
        .join(AIEvaluation.submission)
        .join(EmployeeSubmission.employee)
        .where(SalaryRecommendation.status.in_(self.ACTIVE_RECOMMENDATION_STATUSES))
    )
    if cycle_id:
        query = query.where(EmployeeSubmission.cycle_id == cycle_id)
    if department_filter is not None:
        query = query.where(Employee.department.in_(department_filter))
    query = query.group_by(bucket)
    rows = self.db.execute(query).all()
    return [{'label': row.bucket, 'value': row.count} for row in rows]
```

### 审批流水线状态聚合

```python
def get_approval_pipeline_sql(self, cycle_id: str | None, department_filter: set[str] | None) -> list[dict]:
    """聚合各工作流状态下的评估数量"""
    query = (
        select(
            SalaryRecommendation.status,
            func.count(SalaryRecommendation.id).label('count'),
        )
        .join(SalaryRecommendation.evaluation)
        .join(AIEvaluation.submission)
        .join(EmployeeSubmission.employee)
    )
    if cycle_id:
        query = query.where(EmployeeSubmission.cycle_id == cycle_id)
    if department_filter is not None:
        query = query.where(Employee.department.in_(department_filter))
    query = query.group_by(SalaryRecommendation.status)
    rows = self.db.execute(query).all()
    return [{'label': row.status, 'value': row.count} for row in rows]
```

### Redis 依赖注入

```python
# backend/app/core/redis.py
import redis as redis_lib
from backend.app.core.config import get_settings

_redis_client: redis_lib.Redis | None = None

def get_redis() -> redis_lib.Redis:
    global _redis_client
    if _redis_client is None:
        settings = get_settings()
        _redis_client = redis_lib.from_url(settings.redis_url, decode_responses=True)
    return _redis_client
```

### 部门下钻后端 API

```python
@router.get('/department-drilldown')
def get_department_drilldown(
    department: str = Query(...),
    cycle_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    # 权限检查 + 缓存查找 + SQL 聚合
    ...
```

## 现有代码分析

### 需改造的后端方法

| 方法 | 当前实现 | 改造方向 |
|------|---------|---------|
| `_submissions()` | 全表 SELECT + selectinload | 仅保留给非聚合场景用；聚合查询不再使用此方法 |
| `_evaluations()` | 全表 SELECT + selectinload + Python 过滤 | 各聚合方法直接写 SQL，不再调用此方法 |
| `get_ai_level_distribution()` | Counter 内存聚合 | SQL GROUP BY ai_level |
| `get_overview()` | 多次遍历 evaluations 列表 | 多个 SQL 聚合查询合并 |
| `get_heatmap()` | defaultdict 内存分组 | SQL GROUP BY department (可改为部门下钻数据源) |
| `get_roi_distribution()` | Python Decimal 分桶 | SQL CASE WHEN 分桶 |
| `get_department_insights()` | defaultdict 内存分组 | SQL GROUP BY department + 子查询 |
| `get_action_items()` | 遍历 + 条件计数 | SQL COUNT + WHERE 条件 |

### 需改造的前端组件

| 组件 | 当前 | 改造 |
|------|------|------|
| `DistributionChart.tsx` | 纯 CSS 条形图 | 删除，替换为 ECharts 组件 |
| `HeatmapChart.tsx` | 纯 CSS 卡片网格 | 删除，替换为 ECharts 热力图或部门下钻入口 |
| `OverviewCards.tsx` | 7 个 KPI 卡片 | 改造为 4 个 KPI 卡片 (D-07)，待审批数 30 秒轮询 |
| `DepartmentInsightTable.tsx` | 静态表格 | 添加行展开下钻功能 |
| `ActionSummaryPanel.tsx` | 操作摘要面板 | 可改造为审批流水线图的数据源 |
| `TalentSpotlightPanel.tsx` | 高潜人才列表 | 布局调整，可能降级或融入其他组件 |
| `Dashboard.tsx` | 单列布局 | 改为双列网格布局 (D-09) |

### 新增 API 端点

| 端点 | 用途 |
|------|------|
| `GET /dashboard/kpi-summary` | KPI 卡片数据（待审批数 + 员工数 + 平均调薪 + 等级概览），支持 30 秒轮询 |
| `GET /dashboard/salary-distribution` | 调薪幅度分布直方图数据 |
| `GET /dashboard/approval-pipeline` | 审批流水线各状态计数 |
| `GET /dashboard/department-drilldown` | 指定部门的等级分布和调薪均值 |

## 最新实践

| 旧做法 | 当前做法 | 变更时间 | 影响 |
|--------|---------|---------|------|
| echarts 4.x 按需引入 | echarts 5.x/6.x tree-shaking import | 2023+ | 使用 `import * as echarts from 'echarts'` 或按需 `import { BarChart } from 'echarts/charts'` |
| redis-py 4.x `StrictRedis` | redis-py 5.x `Redis` (合并) | 2024 | `StrictRedis` 已弃用，直接使用 `Redis` |

## 开放问题

1. **Redis 可用性检查**
   - 已知: 当前开发机未检测到 redis-cli。
   - 不确定: 开发者是否已安装 Redis 并运行。
   - 建议: 在后端启动时检查 Redis 连接，开发环境连接失败时输出清晰的安装提示和启动命令，但不阻塞启动（仅看板功能受影响）。注意 D-03 要求 Redis 为必须依赖——如果 Redis 不可用，看板 API 应返回合理的错误而非 500。

2. **现有图表组件的引用清理**
   - 已知: `DistributionChart` 和 `HeatmapChart` 在 `Dashboard.tsx` 中有直接引用。
   - 建议: 替换时一并清理所有引用和 import，确保 build 不报错。

3. **ECharts 包体积**
   - 已知: 完整 echarts 包约 1MB (gzip 后 ~300KB)。
   - 建议: 初期使用完整导入，后续可按需引入减小包体积。

## 环境可用性

| 依赖 | 需要方 | 可用 | 版本 | 备选 |
|------|--------|------|------|------|
| Redis | DASH-02 缓存层 | 未确认 | -- | 无 (D-03 明确要求必须) |
| Node.js | 前端构建 | 是 | -- | -- |
| Python venv | 后端运行 | 是 | 3.13 | -- |
| redis (pip) | Python Redis 客户端 | 是 (requirements.txt) | 5.2.1 | -- |
| echarts (npm) | 前端图表 | 否 (待安装) | 6.0.0 (最新) | -- |
| echarts-for-react (npm) | React 封装 | 否 (待安装) | 3.0.6 (最新) | -- |

**缺失且无备选的依赖:**
- Redis 服务: 需要开发者本地安装并启动 Redis（Windows 可用 WSL 或 Memurai）

**缺失但有备选的依赖:**
- 无

## 验证架构

### 测试框架

| 属性 | 值 |
|------|---|
| 框架 | pytest 8.3.5 (后端) + tsc --noEmit (前端类型检查) |
| 配置文件 | 无专用 pytest.ini (使用默认发现) |
| 快速运行 | `cd D:/wage_adjust && python -m pytest backend/tests/test_services/test_dashboard_service.py -x` |
| 完整套件 | `cd D:/wage_adjust && python -m pytest backend/tests/ -x` |

### 需求到测试映射

| 需求 ID | 行为 | 测试类型 | 自动化命令 | 文件存在 |
|---------|------|---------|-----------|---------|
| DASH-01 | SQL 聚合返回正确分组计数 | unit | `pytest backend/tests/test_services/test_dashboard_service.py -x` | 需改造 |
| DASH-02 | Redis 缓存命中/未命中/过期/角色隔离 | unit | `pytest backend/tests/test_services/test_cache_service.py -x` | Wave 0 新建 |
| DASH-03 | AI 等级分布端点返回正确数据结构 | integration | `pytest backend/tests/test_api/test_dashboard_api.py -x` | 需改造 |
| DASH-04 | 调薪幅度分布端点返回正确区间 | integration | `pytest backend/tests/test_api/test_dashboard_api.py -x` | Wave 0 新建 |
| DASH-05 | 审批流水线端点返回各状态计数 | integration | `pytest backend/tests/test_api/test_dashboard_api.py -x` | Wave 0 新建 |
| DASH-06 | 部门下钻端点返回部门级数据 | integration | `pytest backend/tests/test_api/test_dashboard_api.py -x` | Wave 0 新建 |
| DASH-07 | KPI 端点返回 4 个指标 | integration | `pytest backend/tests/test_api/test_dashboard_api.py -x` | Wave 0 新建 |

### 采样率
- **每次任务提交:** `python -m pytest backend/tests/test_services/test_dashboard_service.py backend/tests/test_api/test_dashboard_api.py -x`
- **每波合并:** `python -m pytest backend/tests/ -x`
- **阶段验收:** 全套件通过 + 前端 `npm run lint` + 手动验证看板页面

### Wave 0 缺口
- [ ] `backend/tests/test_services/test_cache_service.py` -- Redis 缓存服务单元测试
- [ ] `backend/tests/test_api/test_dashboard_api.py` 中新增 DASH-04/05/06/07 测试用例
- [ ] 改造现有 `test_dashboard_service.py` 验证 SQL 聚合正确性

## 来源

### 主要来源 (HIGH 置信度)
- 项目源码: `backend/app/services/dashboard_service.py` -- 现有实现分析
- 项目源码: `backend/app/api/v1/dashboard.py` -- 现有 API 端点
- 项目源码: `backend/app/core/config.py` -- Redis 配置已存在
- npm registry: `echarts@6.0.0`, `echarts-for-react@3.0.6` -- 版本验证

### 次要来源 (MEDIUM 置信度)
- [echarts-for-react npm](https://www.npmjs.com/package/echarts-for-react) -- React 封装用法
- [DEV Community - ECharts + React + TypeScript](https://dev.to/manufac/using-apache-echarts-with-react-and-typescript-353k) -- TypeScript 集成模式
- [Redis 官方 FastAPI 教程](https://redis.io/tutorials/develop/python/fastapi/) -- Redis + FastAPI 集成

### 第三方来源 (LOW 置信度)
- 无

## 元数据

**置信度细分:**
- 标准技术栈: HIGH -- echarts 和 redis 版本从 npm registry 和 requirements.txt 验证
- 架构模式: HIGH -- 基于对现有代码的深入分析，模式明确
- 常见陷阱: HIGH -- 基于项目实际代码结构和已知的 SQLAlchemy/Redis 最佳实践

**研究日期:** 2026-03-28
**有效期至:** 2026-04-28 (技术栈稳定，30 天有效)
