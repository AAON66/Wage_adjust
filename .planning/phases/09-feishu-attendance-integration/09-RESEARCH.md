# Phase 9: 飞书考勤集成 - 研究报告

**研究日期:** 2026-03-28
**领域:** 飞书多维表格 API 集成 / 定时任务调度 / 考勤数据管理
**总体置信度:** HIGH

## 摘要

本阶段需要将飞书多维表格中的员工考勤数据同步到系统中，在调薪审批页面和独立考勤管理页面展示考勤概览。核心技术挑战包括：飞书 Bitable API 的认证与数据拉取、APScheduler 嵌入 FastAPI 进程的定时同步、App Secret 的 AES-256-GCM 加密存储、UI 可配置的字段映射以及增量/全量两种同步策略。

项目已有成熟的 AES-256-GCM 加密方案（`backend/app/core/encryption.py`）、角色权限工厂（`require_roles`）、httpx HTTP 客户端以及完整的 SQLAlchemy + Alembic 迁移体系，可大量复用。飞书 API 本身比较稳定，但需要注意 token 2 小时有效期的自动刷新、分页拉取的 page_token 机制、以及增量同步中 `last_modified_time` 字段的使用方式。

**核心建议:** 使用 APScheduler 3.x（稳定版）的 `AsyncIOScheduler` 通过 FastAPI lifespan 管理生命周期；飞书 API 调用使用现有 httpx 同步客户端；加密复用 `encryption.py` 中的 AES-256-GCM 方案但使用独立密钥。

<user_constraints>
## 用户约束（来自 CONTEXT.md）

### 锁定决策
- **D-01:** App ID/Secret **数据库加密存储**。复用项目已有的加密方案，管理员通过 UI 配置。
- **D-02:** Token 自动刷新——tenant_access_token 有效期 2 小时，系统在调用前检查过期时间，过期时自动重新获取。
- **D-03:** **UI 可配置映射**。管理员在配置页面设置「飞书字段名 -> 系统字段名」映射关系。系统固定字段：employee_no（关联键）、attendance_rate、absence_days、overtime_hours、late_count、early_leave_count。飞书字段名可自定义。
- **D-04:** 按 employee_no 匹配员工，飞书表格中必须有一个字段映射到员工工号。
- **D-05:** 使用 **APScheduler**（内嵌 FastAPI 进程），不依赖额外 Celery worker。配置定时同步时间（如每天 06:00）。
- **D-06:** 定时同步使用增量拉取（基于上次同步时间）。
- **D-07:** 默认**增量拉取**（基于上次同步时间，仅获取新增/修改记录）。
- **D-08:** 手动提供两个按钮：「全量同步」（拉取全部 + upsert）和「增量同步」（仅新增/修改）。
- **D-09:** 同步失败**自动重试 3 次**（间隔递增），全部失败后记录错误日志，在管理页面展示错误状态。不影响调薪流程。
- **D-10:** 考勤概览在**两个位置**展示：1) 人工调薪窗口内嵌（该员工的考勤 KPI 卡片）2) 独立考勤管理页面（所有员工的卡片面板，支持搜索筛选）
- **D-11:** 展示字段：出勤率、缺勤天数、加班时长、迟到次数、早退次数。底部标注「数据截至：YYYY-MM-DD HH:mm」时间戳。
- **D-12:** 页面包含：员工考勤卡片面板（搜索+筛选）、同步状态卡片（上次同步时间/状态/记录数）、手动同步按钮（全量+增量）、飞书配置入口按钮。
- **D-13:** 页面权限：**admin + hrbp** 可见。飞书配置修改权限仅 admin。
- **D-14:** **单页表单**布局。分两个区域：「连接配置」（App ID / App Secret / 多维表格 ID / 定时同步时间）和「字段映射」（双列映射表：左飞书字段名、右系统字段名）。底部保存按钮。
- **D-15:** 飞书配置页面**仅 admin** 可访问。

### Claude 自主决策范围
- APScheduler 的具体调度配置
- 考勤卡片和配置页面的视觉样式
- 飞书 API 错误码到中文错误消息的映射
- 增量同步的「修改时间」字段检测逻辑

### 延后事项（不在范围内）
- 考勤数据影响调薪计算——本阶段考勤仅作参考展示，不自动影响调薪
- 考勤数据导出——不在当前范围
- 飞书审批流对接——仅对接多维表格
- Mock 数据——用户明确不需要开发环境 Mock
</user_constraints>

<phase_requirements>
## 阶段需求

| ID | 描述 | 研究支持 |
|----|------|----------|
| ATT-01 | 系统通过飞书多维表格 API 接入员工考勤数据，同步出勤率、缺勤天数、加班时长/次数、迟到次数、早退次数 | 飞书 Bitable Search Records API（POST）支持分页拉取 + automatic_fields 返回修改时间；httpx 已在项目中 |
| ATT-02 | 支持手动触发同步——HR 可在系统内点击「同步考勤数据」按钮，立即从飞书拉取最新数据 | 后端 API 触发同步任务，前端两个按钮（全量/增量）对应不同参数 |
| ATT-03 | 支持定时自动同步——系统每天定时（可配置时间）自动从飞书多维表格拉取最新考勤数据 | APScheduler 3.x AsyncIOScheduler 嵌入 FastAPI lifespan，CronTrigger 支持可配置时间 |
| ATT-04 | 飞书连接配置（App ID、App Secret、多维表格 ID、字段映射）在后台管理页面中可配置 | FeishuConfig 模型加密存储 Secret，前端单页表单配置 |
| ATT-05 | 人工调薪页面在薪资调整区域展示该员工当前考勤概览 | SalarySimulator 页面内嵌 AttendanceKpiCard 组件 |
| ATT-06 | 考勤数据展示说明同步时间（「数据截至：YYYY-MM-DD HH:mm」） | AttendanceRecord 模型存储 synced_at 时间戳 |
| ATT-07 | 若飞书同步失败，系统记录错误日志并在管理页面展示上次同步状态 | FeishuSyncLog 模型记录每次同步结果；自动重试 3 次递增间隔 |
</phase_requirements>

## 标准技术栈

### 核心

| 库 | 版本 | 用途 | 选择理由 |
|----|------|------|----------|
| APScheduler | 3.11.x (稳定版) | 定时任务调度 | 用户决策 D-05 锁定；4.0 仍为 pre-release（alpha），3.x 是生产级选择 |
| httpx | 0.28.1 (已安装) | 飞书 API HTTP 调用 | 项目已有，用于 DeepSeek 调用，直接复用 |
| cryptography | 44.0.2 (已安装) | App Secret 加密存储 | 项目已有 AES-256-GCM 方案，复用 `encryption.py` 模式 |
| SQLAlchemy | 2.0.36 (已安装) | ORM 模型与数据持久化 | 项目标准 |
| Alembic | 1.14.0 (已安装) | 数据库迁移 | 项目标准 |

### 辅助

| 库 | 版本 | 用途 | 使用场景 |
|----|------|------|----------|
| Pydantic | 2.10.3 (已安装) | 请求/响应 Schema 验证 | FeishuConfig、AttendanceRecord 的 API 层校验 |

### 替代方案

| 替代 | 可选 | 取舍 |
|------|------|------|
| APScheduler 3.x | Celery Beat | 用户已锁定 APScheduler；Celery 需要额外 worker 进程 |
| APScheduler 3.x | APScheduler 4.x | 4.0 仍是 alpha，API 不稳定，不适合生产 |
| httpx 同步调用 | aiohttp 异步调用 | 同步足够（飞书 API 调用频率低），异步增加复杂性无实际收益 |

**安装命令:**
```bash
pip install APScheduler==3.11.2
```

**版本验证:** APScheduler 3.11.2 是 2025 年 12 月发布的最新稳定版。4.0.0a6 是 2025 年 4 月的 alpha 版本，不推荐生产使用。

## 架构模式

### 推荐项目结构
```
backend/app/
├── models/
│   ├── feishu_config.py         # 飞书连接配置（加密 Secret + 字段映射 JSON）
│   ├── attendance_record.py     # 员工考勤快照
│   └── feishu_sync_log.py       # 同步日志
├── schemas/
│   ├── feishu.py                # FeishuConfig 请求/响应 + 字段映射
│   └── attendance.py            # 考勤记录请求/响应
├── services/
│   ├── feishu_service.py        # 飞书 API 调用 + Token 管理 + 数据同步
│   └── attendance_service.py    # 考勤查询 + 管理
├── api/v1/
│   ├── feishu.py                # 飞书配置 + 手动同步端点
│   └── attendance.py            # 考勤数据查询端点
└── scheduler/
    └── feishu_scheduler.py      # APScheduler 配置 + 定时任务注册

frontend/src/
├── pages/
│   ├── AttendanceManagement.tsx  # 独立考勤管理页面
│   └── FeishuConfig.tsx          # 飞书配置页面
├── components/
│   └── attendance/
│       ├── AttendanceKpiCard.tsx  # 单员工考勤卡片（复用于两处展示）
│       ├── SyncStatusCard.tsx     # 同步状态卡片
│       └── FieldMappingTable.tsx  # 字段映射表格
└── services/
    ├── feishuService.ts          # 飞书配置 + 同步 API
    └── attendanceService.ts      # 考勤数据查询 API
```

### 模式 1: 飞书 Token 管理（内存缓存 + 自动刷新）

**场景:** D-02 要求 tenant_access_token 2 小时有效期，调用前自动检查刷新。

**方案:** FeishuService 内部维护 token + 过期时间戳，每次调用前检查是否过期（提前 5 分钟刷新），过期则重新请求。

```python
# backend/app/services/feishu_service.py
from __future__ import annotations

import time
import logging
import httpx
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

FEISHU_BASE_URL = 'https://open.feishu.cn/open-apis'
TOKEN_REFRESH_BUFFER = 300  # 提前 5 分钟刷新


class FeishuService:
    def __init__(self, db: Session):
        self.db = db
        self._token: str | None = None
        self._token_expires_at: float = 0

    def _ensure_token(self, app_id: str, app_secret: str) -> str:
        """获取有效的 tenant_access_token，过期时自动刷新。"""
        now = time.time()
        if self._token and now < self._token_expires_at - TOKEN_REFRESH_BUFFER:
            return self._token

        resp = httpx.post(
            f'{FEISHU_BASE_URL}/auth/v3/tenant_access_token/internal',
            json={'app_id': app_id, 'app_secret': app_secret},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get('code') != 0:
            raise RuntimeError(f'飞书 Token 获取失败: {data.get("msg")}')
        self._token = data['tenant_access_token']
        self._token_expires_at = now + data.get('expire', 7200)
        return self._token
```

### 模式 2: APScheduler 嵌入 FastAPI lifespan

**场景:** D-05 要求内嵌 FastAPI 进程，不依赖 Celery worker。

```python
# backend/app/scheduler/feishu_scheduler.py
from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

scheduler = AsyncIOScheduler()


def start_scheduler(sync_hour: int = 6, sync_minute: int = 0) -> None:
    """启动定时同步调度器。"""
    from backend.app.scheduler.feishu_jobs import run_incremental_sync
    scheduler.add_job(
        run_incremental_sync,
        trigger=CronTrigger(hour=sync_hour, minute=sync_minute),
        id='feishu_attendance_sync',
        replace_existing=True,
    )
    scheduler.start()


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
```

在 `main.py` lifespan 中集成:
```python
@asynccontextmanager
async def lifespan(_: FastAPI):
    # ... 现有启动逻辑 ...
    from backend.app.scheduler.feishu_scheduler import start_scheduler, stop_scheduler
    start_scheduler()
    yield
    stop_scheduler()
```

### 模式 3: 增量同步 + 全量同步双模式

**场景:** D-07/D-08 要求增量拉取（基于 last_modified_time）和全量拉取两种模式。

```python
def sync_attendance(self, mode: str = 'incremental') -> SyncResult:
    """同步考勤数据。mode='full' 全量同步，mode='incremental' 增量同步。"""
    config = self._get_feishu_config()
    token = self._ensure_token(config.app_id, config.decrypted_app_secret)

    last_sync = self._get_last_successful_sync_time() if mode == 'incremental' else None

    records = self._fetch_all_records(
        token=token,
        app_token=config.bitable_app_token,
        table_id=config.bitable_table_id,
        field_mapping=config.field_mapping,
        since=last_sync,  # None = 全量
    )
    # upsert 到 attendance_record 表
    result = self._upsert_records(records)
    self._log_sync(mode=mode, result=result)
    return result
```

### 模式 4: 加密存储复用

**场景:** D-01 要求 App Secret 数据库加密存储，复用现有加密方案。

**方案:** 复用 `encryption.py` 中的 `encrypt_national_id` / `decrypt_national_id` 函数（重命名为通用版本），或直接创建对等的 `encrypt_value` / `decrypt_value`。使用独立的加密密钥环境变量 `FEISHU_ENCRYPTION_KEY`。

```python
# backend/app/models/feishu_config.py
class FeishuConfig(UUIDPrimaryKeyMixin, CreatedAtMixin, UpdatedAtMixin, Base):
    __tablename__ = 'feishu_configs'

    app_id: Mapped[str] = mapped_column(String(128), nullable=False)
    encrypted_app_secret: Mapped[str] = mapped_column(String(512), nullable=False)
    bitable_app_token: Mapped[str] = mapped_column(String(128), nullable=False)
    bitable_table_id: Mapped[str] = mapped_column(String(128), nullable=False)
    field_mapping: Mapped[str] = mapped_column(Text, nullable=False, default='{}')  # JSON
    sync_hour: Mapped[int] = mapped_column(Integer, nullable=False, default=6)
    sync_minute: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
```

### 反模式

- **不要在 FeishuConfig 中明文存储 App Secret:** 必须加密存储，API 响应中也需脱敏（仅返回最后 4 位）
- **不要在定时任务中直接使用全局 DB Session:** APScheduler job 必须创建独立的 DB Session，避免跨请求 Session 泄漏
- **不要硬编码飞书字段名:** 字段映射必须通过 FeishuConfig.field_mapping 配置化
- **不要忽略飞书 API 分页:** 单次最多 500 条，必须循环 page_token 直到 has_more=false
- **不要在同步失败时影响调薪主流程:** 考勤同步是辅助功能，失败只记录日志

## 不要手工实现

| 问题 | 不要自建 | 使用现有方案 | 原因 |
|------|----------|-------------|------|
| 定时调度 | 自建 cron 循环 | APScheduler 3.x | 时区处理、错过任务补偿、线程安全 |
| AES 加密 | 自建加密轮子 | `cryptography` AESGCM | 已有方案，已验证 |
| HTTP 重试 | 自建重试逻辑 | httpx + tenacity 或手动重试 | httpx 本身不含重试；但 3 次递增重试逻辑简单，可手写 |
| 分页遍历 | 一次性拉取 | 循环 page_token | 飞书限制单次 500 条 |

**关键洞察:** 飞书 API 自身比较简单（REST + JSON），不需要 SDK。httpx 直接调用即可，避免引入额外 `lark-oapi` SDK 增加依赖。

## 飞书 API 详细规格

### 认证: 获取 tenant_access_token

```
POST https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal
Content-Type: application/json

{
  "app_id": "cli_xxx",
  "app_secret": "xxx"
}

Response:
{
  "code": 0,
  "msg": "ok",
  "tenant_access_token": "t-caecc734c2e...",
  "expire": 7200
}
```

- Token 有效期 **7200 秒（2 小时）**
- 建议提前 5 分钟刷新
- 置信度: **HIGH**（官方文档 + 多源验证）

### 查询记录: Search Records API（推荐）

```
POST https://open.feishu.cn/open-apis/bitable/v1/apps/:app_token/tables/:table_id/records/search
Authorization: Bearer {tenant_access_token}
Content-Type: application/json

{
  "page_size": 500,
  "page_token": "",
  "automatic_fields": true,
  "filter": {
    "conjunction": "and",
    "conditions": [
      {
        "field_name": "修改时间",
        "operator": "isGreater",
        "value": ["1711872000000"]
      }
    ]
  }
}
```

关键参数:
- `page_size`: 最大 500，默认 20
- `page_token`: 分页标记
- `automatic_fields`: 设为 true 返回 `last_modified_time`
- `filter`: 支持 AND/OR 条件组合
- 频率限制: **20 次/秒**

响应结构:
```json
{
  "code": 0,
  "data": {
    "has_more": true,
    "page_token": "xxx",
    "total": 1234,
    "items": [
      {
        "record_id": "recXXX",
        "fields": { "工号": "E001", "出勤率": 0.95, ... },
        "last_modified_time": 1711872000000,
        "created_time": 1711800000000
      }
    ]
  }
}
```

### 增量同步策略

飞书 Search Records API 支持通过 `last_modified_time` 字段 + `isGreater` 操作符实现增量查询。但需注意:

1. `last_modified_time` 是记录的系统修改时间，毫秒时间戳
2. 需设置 `automatic_fields: true` 才会返回此字段
3. 增量拉取时，filter 中使用上次同步成功的时间戳

**置信度:** MEDIUM — 官方文档确认 `automatic_fields` 返回 `last_modified_time`，但 filter 对此字段的支持需实际测试验证。如果不支持对系统字段 filter，备选方案是拉取全部记录后在应用层按时间过滤。

### 注意事项

- **List Records API 已标记为 deprecated**，官方推荐使用 Search Records API
- Checkbox 类型字段为空时不返回（需在代码中默认处理为 false/0）
- 文件 token 仅在当前多维表格内有效
- 开启高级权限时需额外处理

## 常见陷阱

### 陷阱 1: APScheduler job 中的 DB Session 管理
**问题:** APScheduler 的定时任务在独立线程/协程中执行，不在 FastAPI 请求上下文中，直接使用 `get_db()` 依赖会失败。
**原因:** FastAPI 的 `Depends` 系统只在请求生命周期内有效。
**解决:** 在 job 函数中手动创建 Session：
```python
from backend.app.core.database import SessionLocal

def run_incremental_sync():
    db = SessionLocal()
    try:
        service = FeishuService(db)
        service.sync_attendance(mode='incremental')
        db.commit()
    except Exception:
        db.rollback()
        logger.exception('定时考勤同步失败')
    finally:
        db.close()
```
**警告信号:** 出现 `No current request` 或 `Session is not active` 错误

### 陷阱 2: Token 并发刷新竞态
**问题:** 多个同步请求同时发现 token 过期，触发多次 token 刷新。
**原因:** FeishuService 在多次 API 调用中共享 token 状态。
**解决:** 使用线程锁保护 token 刷新逻辑，或使用 `threading.Lock`。在本场景中由于同步频率低（每天一次 + 偶尔手动），实际并发风险极低，简单的锁即可。

### 陷阱 3: 飞书字段类型不匹配
**问题:** 飞书多维表格字段类型多样（数字、文本、日期、百分比等），与系统期望的 float/int 类型不一致。
**原因:** 用户可能在飞书中使用文本类型存储数字，或百分比字段返回 0.95 而非 95。
**解决:** 在字段映射转换层添加类型强制转换 + 异常处理，单条记录转换失败不影响其他记录。
**警告信号:** 同步后数据全为 0 或 None

### 陷阱 4: 加密密钥管理
**问题:** 复用 `national_id_encryption_key` 会导致飞书配置与身份证号共用密钥，密钥泄露影响范围扩大。
**原因:** 安全最佳实践要求不同用途使用不同密钥。
**解决:** 新增独立的 `FEISHU_ENCRYPTION_KEY` 环境变量，复用相同的 AES-256-GCM 加密函数。

### 陷阱 5: 同步期间并发请求
**问题:** 用户点击手动同步按钮后立即再次点击，导致两个同步任务并行执行。
**原因:** 缺少去重机制。
**解决:** 后端维护一个同步状态标记（数据库或内存锁），同步进行中拒绝新的同步请求并返回友好提示。

### 陷阱 6: employee_no 匹配失败静默丢数据
**问题:** 飞书表格中的工号与系统 Employee.employee_no 不匹配（格式差异如前导零）。
**原因:** 两个系统中的员工编号格式可能不一致。
**解决:** 在同步结果中明确记录「未匹配记录数」和具体的未匹配工号列表，展示在同步日志中。

## 代码示例

### 飞书记录分页拉取

```python
# Source: 基于飞书官方 API 文档 Search Records 端点
def _fetch_all_records(
    self,
    token: str,
    app_token: str,
    table_id: str,
    field_mapping: dict[str, str],
    since: int | None = None,
) -> list[dict]:
    """拉取飞书多维表格全部匹配记录，自动处理分页。"""
    url = f'{FEISHU_BASE_URL}/bitable/v1/apps/{app_token}/tables/{table_id}/records/search'
    headers = {'Authorization': f'Bearer {token}'}

    body: dict = {
        'page_size': 500,
        'automatic_fields': True,
    }

    if since is not None:
        body['filter'] = {
            'conjunction': 'and',
            'conditions': [{
                'field_name': '最后修改时间',
                'operator': 'isGreater',
                'value': [str(since)],
            }],
        }

    all_records = []
    page_token = ''

    while True:
        if page_token:
            body['page_token'] = page_token
        resp = httpx.post(url, headers=headers, json=body, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        if data.get('code') != 0:
            raise RuntimeError(f'飞书 API 错误: {data.get("msg")}')

        items = data.get('data', {}).get('items', [])
        for item in items:
            parsed = self._map_fields(item['fields'], field_mapping)
            if parsed:
                parsed['feishu_record_id'] = item['record_id']
                parsed['last_modified_time'] = item.get('last_modified_time')
                all_records.append(parsed)

        if not data.get('data', {}).get('has_more', False):
            break
        page_token = data['data']['page_token']

    return all_records
```

### 重试机制

```python
import time
import logging

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAYS = [5, 15, 45]  # 递增间隔（秒）


def sync_with_retry(service: FeishuService, mode: str) -> SyncResult:
    """带重试的考勤同步。"""
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            return service.sync_attendance(mode=mode)
        except Exception as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                delay = RETRY_DELAYS[attempt]
                logger.warning(
                    '考勤同步失败 (第 %d/%d 次)，%d 秒后重试: %s',
                    attempt + 1, MAX_RETRIES, delay, e,
                )
                time.sleep(delay)
    # 全部失败
    logger.error('考勤同步在 %d 次重试后仍然失败: %s', MAX_RETRIES, last_error)
    raise last_error
```

### 数据库模型示例

```python
# backend/app/models/attendance_record.py
from __future__ import annotations

from datetime import datetime
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.database import Base
from backend.app.models.mixins import UUIDPrimaryKeyMixin, CreatedAtMixin, UpdatedAtMixin


class AttendanceRecord(UUIDPrimaryKeyMixin, CreatedAtMixin, UpdatedAtMixin, Base):
    __tablename__ = 'attendance_records'
    __table_args__ = (
        UniqueConstraint('employee_id', 'period', name='uq_attendance_employee_period'),
    )

    employee_id: Mapped[str] = mapped_column(
        String(36), ForeignKey('employees.id'), nullable=False
    )
    employee_no: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    period: Mapped[str] = mapped_column(String(32), nullable=False)  # 如 '2026-03'
    attendance_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    absence_days: Mapped[float | None] = mapped_column(Float, nullable=True)
    overtime_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    late_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    early_leave_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    feishu_record_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
```

## 技术演进

| 旧方案 | 当前方案 | 变更时间 | 影响 |
|--------|---------|---------|------|
| List Records API | Search Records API | 2024 | List Records 已 deprecated，Search 支持更丰富的过滤 |
| APScheduler 3.x | APScheduler 4.x (alpha) | 2025 | 4.0 重新设计了 Task/Schedule/Job 概念，但仍为 alpha，不可生产使用 |

**已弃用/过时:**
- 飞书 `GET .../records`（List Records）：已标记 deprecated，应使用 `POST .../records/search`
- APScheduler `@app.on_event("startup")`：FastAPI 已弃用此模式，应使用 lifespan context manager

## 开放问题

1. **飞书 Search Records 是否支持对 `last_modified_time` 系统字段做 filter**
   - 已知: `automatic_fields=true` 可在响应中返回此字段
   - 不确定: filter 条件中是否能直接使用此系统字段名
   - 建议: 实现时先尝试系统字段 filter，失败则降级为拉取全量 + 应用层过滤
   - 置信度: MEDIUM

2. **多维表格中考勤数据的粒度**
   - 已知: 用户要求同步出勤率等 6 个字段
   - 不确定: 是否存在月度 period 字段，或每行代表一个员工的当前累计数据
   - 建议: 模型设计支持 period 字段用于多周期存储，如飞书表格无 period 则使用同步月份

## 环境可用性

| 依赖 | 需要方 | 可用 | 版本 | 备用方案 |
|------|--------|------|------|----------|
| httpx | 飞书 API 调用 | 是 | 0.28.1 | -- |
| cryptography | Secret 加密 | 是 | 44.0.2 | -- |
| APScheduler | 定时同步 | 否（需安装） | -- | `pip install APScheduler==3.11.2` |
| Redis | 可选（APScheduler jobstore） | 是 | 已安装 | 使用内存 jobstore（默认） |
| 飞书开放平台应用 | 所有飞书 API 调用 | 未知 | -- | 需用户在飞书后台创建应用并提供 App ID/Secret |

**缺少但有备用方案的依赖:**
- APScheduler: 需要 `pip install`，添加到 `requirements.txt`

**需要人工操作的外部依赖:**
- 飞书开放平台应用创建 + 权限配置（`bitable:app`, `bitable:record:read`）——这是用户侧操作

## 验证架构

### 测试框架
| 属性 | 值 |
|------|-----|
| 框架 | pytest 8.3.5 |
| 配置文件 | 无独立配置文件，使用默认 |
| 快速运行 | `pytest backend/tests/test_services/test_feishu_service.py -x` |
| 全量运行 | `pytest backend/tests/ -x` |

### 阶段需求 -> 测试映射
| 需求 ID | 行为 | 测试类型 | 自动化命令 | 文件存在? |
|---------|------|----------|-----------|-----------|
| ATT-01 | 飞书 API 调用 + 字段映射 + 记录存储 | unit | `pytest backend/tests/test_services/test_feishu_service.py -x` | 否 Wave 0 |
| ATT-02 | 手动同步 API 端点触发同步 | integration | `pytest backend/tests/test_api/test_attendance.py -x` | 否 Wave 0 |
| ATT-03 | APScheduler 定时任务注册 + 执行 | unit | `pytest backend/tests/test_services/test_feishu_scheduler.py -x` | 否 Wave 0 |
| ATT-04 | 配置 CRUD + 加密存储 | unit | `pytest backend/tests/test_services/test_feishu_config.py -x` | 否 Wave 0 |
| ATT-05 | 考勤 API 返回单员工考勤数据 | integration | `pytest backend/tests/test_api/test_attendance.py::test_employee_attendance -x` | 否 Wave 0 |
| ATT-06 | 响应包含 synced_at 时间戳 | unit | `pytest backend/tests/test_services/test_attendance_service.py -x` | 否 Wave 0 |
| ATT-07 | 同步失败重试 + 日志记录 | unit | `pytest backend/tests/test_services/test_feishu_service.py::test_sync_retry -x` | 否 Wave 0 |

### 采样频率
- **每任务提交:** `pytest backend/tests/test_services/test_feishu_service.py -x`
- **每 wave 合并:** `pytest backend/tests/ -x`
- **阶段验收:** 全量测试通过

### Wave 0 缺口
- [ ] `backend/tests/test_services/test_feishu_service.py` — 覆盖 ATT-01, ATT-07
- [ ] `backend/tests/test_services/test_feishu_config.py` — 覆盖 ATT-04
- [ ] `backend/tests/test_services/test_attendance_service.py` — 覆盖 ATT-05, ATT-06
- [ ] `backend/tests/test_api/test_attendance.py` — 覆盖 ATT-02, ATT-05
- [ ] `backend/tests/test_services/test_feishu_scheduler.py` — 覆盖 ATT-03
- [ ] `backend/tests/fixtures/feishu_fixtures.py` — 飞书 API 响应 mock 数据

## 项目约束（来自 CLAUDE.md）

- 前端: React + TypeScript + Tailwind CSS
- 后端: FastAPI + SQLAlchemy + Pydantic
- 所有 schema 变更通过 Alembic migration
- 所有关键配置（系数、阈值）必须配置化，不允许硬编码
- 对外 API 版本化 `/api/v1/`
- 使用 `require_roles` 进行权限控制
- 角色权限: `frontend/src/utils/roleAccess.ts` 管理前端模块可见性
- 加密: `backend/app/core/encryption.py` 已有 AES-256-GCM 方案
- 服务层 DI: 所有协作者可选并有默认值
- 命名: snake_case（Python）、PascalCase（React 组件）、camelCase（React 非组件）

## 来源

### 主要来源（HIGH 置信度）
- [飞书开放平台 Bitable API 文档](https://open.feishu.cn/document/server-docs/docs/bitable-v1/bitable-overview) — API 端点、分页、频率限制
- [飞书 Search Records API](https://open.feishu.cn/document/docs/bitable-v1/app-table-record/search) — POST 查询端点、filter 语法、automatic_fields
- [飞书 tenant_access_token 文档](https://open.feishu.cn/document/server-docs/authentication-management/access-token/tenant_access_token_internal) — Token 获取端点、有效期
- [APScheduler PyPI](https://pypi.org/project/APScheduler/) — 版本信息
- [APScheduler 3.x 文档](https://apscheduler.readthedocs.io/en/3.x/userguide.html) — AsyncIOScheduler 用法

### 次要来源（MEDIUM 置信度）
- [飞书 Bitable FAQ](https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/reference/bitable-v1/faq) — Checkbox 空值、高级权限注意事项
- [Sentry: Schedule tasks with FastAPI](https://sentry.io/answers/schedule-tasks-with-fastapi/) — APScheduler + lifespan 集成模式

### 三级来源（LOW 置信度）
- [CSDN 飞书 API 系列文章](https://blog.csdn.net/qq_45476428/article/details/137213076) — Python 分页拉取实践（需验证）

## 元数据

**置信度分解:**
- 标准技术栈: HIGH — 所有库在项目中已有或有明确的官方文档
- 架构模式: HIGH — 遵循项目现有模式（service/model/api 分层）
- 飞书 API: HIGH — 官方文档确认端点和参数
- 增量同步 filter: MEDIUM — 系统字段是否支持 filter 条件需实际验证
- APScheduler 集成: HIGH — 3.x AsyncIOScheduler + FastAPI lifespan 是成熟模式
- 陷阱: HIGH — 基于项目实际代码分析和飞书 API 文档

**研究日期:** 2026-03-28
**有效期至:** 2026-04-28（飞书 API 稳定，APScheduler 3.x 稳定）
