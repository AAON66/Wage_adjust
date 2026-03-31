# Architecture Patterns: v1.1 Feature Integration

**Domain:** Enterprise Salary Adjustment Platform - v1.1 feature additions
**Researched:** 2026-03-30
**Overall confidence:** HIGH (based on direct codebase analysis)

## Recommended Architecture

All 5 features integrate into the existing `api/ -> services/ -> engines/ -> models/` layered architecture. No new layers are needed. The key principle: **add new models/services/engines alongside existing ones, modify existing ones minimally.**

### Component Map: What's New vs What Changes

```
NEW components (create from scratch):
  backend/app/models/file_share_request.py       -- Feature 2
  backend/app/engines/eligibility_engine.py       -- Feature 4
  backend/app/services/file_share_service.py      -- Feature 2
  backend/app/services/eligibility_service.py     -- Feature 4
  backend/app/api/v1/file_sharing.py              -- Feature 2
  backend/app/api/v1/eligibility.py               -- Feature 4
  frontend/src/pages/BindingManagement.tsx         -- Feature 1
  frontend/src/components/file/ShareRequestPanel.tsx     -- Feature 2
  frontend/src/components/file/ShareRequestList.tsx      -- Feature 2
  frontend/src/components/salary/EligibilityBadge.tsx    -- Feature 4

MODIFIED components (extend existing):
  backend/app/services/file_service.py            -- Feature 2: change dedup from reject to warn+share
  backend/app/services/identity_binding_service.py -- Feature 1: add manual bind/unbind
  backend/app/api/v1/users.py                     -- Feature 1: binding endpoints
  frontend/src/utils/roleAccess.ts                -- Feature 3: grouped navigation
  frontend/src/components/layout/AppShell.tsx      -- Feature 3: grouped sidebar
  frontend/src/components/evaluation/SalaryResultCard.tsx -- Feature 5: collapsible sections
  frontend/src/pages/EvaluationDetail.tsx          -- Feature 4+5: eligibility + collapsible
  frontend/src/pages/MyReview.tsx                  -- Feature 5: collapsible salary
  frontend/src/App.tsx                             -- Feature 1+3: new routes
```

---

## Feature 1: Account-Employee Binding (账号-员工绑定加固)

### Current State

- `User.employee_id` FK to `employees.id` exists (nullable, unique)
- `IdentityBindingService` does auto-bind via `id_card_no` matching
- No dedicated UI for manual binding management -- binding happens silently in backend
- `SettingsPage` and `UserAdminPage` exist but don't expose binding controls

### Architecture Changes

**Backend -- minimal:**

| Component | Change | Details |
|-----------|--------|---------|
| `IdentityBindingService` | ADD methods | `manual_bind(user_id, employee_id)`, `unbind(user_id)`, `get_binding_status(user_id)` |
| `api/v1/users.py` | ADD endpoints | `POST /users/{id}/bind`, `DELETE /users/{id}/bind`, `GET /users/{id}/binding-status` |
| `User` model | NO CHANGE | `employee_id` FK already exists and works |

**Frontend:**

| Component | Type | Details |
|-----------|------|---------|
| `BindingManagement.tsx` page OR section in `UserAdminPage` | NEW or MODIFY | Admin/HRBP can search employee, bind/unbind from user record |
| `SettingsPage.tsx` | MODIFY | Show binding status for current user, self-service bind if `id_card_no` matches |

**Data flow:**

```
Admin clicks "Bind" on UserAdmin
  -> POST /api/v1/users/{user_id}/bind { employee_id }
  -> IdentityBindingService.manual_bind()
  -> Validates no conflicting binds
  -> Sets User.employee_id = employee_id
  -> Returns updated UserProfile with employee_name, employee_no
```

**Access control:** Admin/HRBP can bind any user. Employees can only self-bind (if `id_card_no` matches). Use existing `require_roles()` dependency.

### Why This Design

The `IdentityBindingService` already encapsulates all bind logic and conflict detection. Adding `manual_bind`/`unbind` methods is a natural extension. No new model needed -- the FK is already there.

---

## Feature 2: File Upload Sharing/Approval (文件上传共享申请机制)

### Current State

- `FileService._check_duplicate()` does global dedup by `(file_name, content_hash)`
- On duplicate found: raises `ValueError` and rejects upload entirely
- `UploadedFile` tracks `submission_id` (owner's submission), `content_hash`, `owner_contribution_pct`
- `ProjectContributor` model already exists for multi-contributor tracking

### Architecture Changes

**New model: `FileShareRequest`**

```python
class FileShareRequest(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = 'file_share_requests'

    requester_submission_id: Mapped[str]     # submission requesting access
    original_file_id: Mapped[str]            # the UploadedFile being shared
    status: Mapped[str]                      # pending -> approved / rejected
    requester_note: Mapped[str | None]       # "I co-authored this"
    responder_note: Mapped[str | None]       # "Approved, 30% contribution"
    contribution_pct: Mapped[float | None]   # agreed percentage for requester
    responded_at: Mapped[datetime | None]
    responded_by: Mapped[str | None]         # user_id of responder
```

**New service: `FileShareService`**

```
FileShareService
  +-- create_share_request(requester_submission_id, original_file_id, note)
  +-- list_pending_requests(user_id)       # for file owner
  +-- list_my_requests(submission_id)      # for requester
  +-- approve_request(request_id, contribution_pct, note)
  +-- reject_request(request_id, note)
  +-- _clone_file_to_submission(original_file_id, target_submission_id, contribution_pct)
```

**Modified: `FileService._check_duplicate()`**

Change from "reject" to "warn + offer share":
```python
# Before: raises ValueError
# After: returns DuplicateInfo(existing_file, owner_submission, can_request_share=True)
```

The upload endpoint returns a warning payload instead of 409, letting the frontend show a dialog: "This file was already uploaded by [Employee Name]. Request to share?"

**New API routes: `api/v1/file_sharing.py`**

```
POST   /submissions/{id}/share-requests          # create request
GET    /share-requests/pending                   # list my pending (as owner)
GET    /submissions/{id}/share-requests           # list requests for a submission
PATCH  /share-requests/{id}/approve              # approve
PATCH  /share-requests/{id}/reject               # reject
```

**Frontend components:**

| Component | Type | Details |
|-----------|------|---------|
| `ShareRequestPanel.tsx` | NEW | Dialog shown when duplicate detected: "Request sharing?" |
| `ShareRequestList.tsx` | NEW | Notification-style list of pending share requests for file owners |
| `FileUploadPanel.tsx` | MODIFY | Integrate duplicate-warning flow instead of hard error |

**Data flow (happy path):**

```
Employee B uploads file that Employee A already uploaded
  -> FileService detects duplicate by content_hash
  -> Returns 200 with { duplicate: true, original_file_id, owner_name }
  -> Frontend shows ShareRequestPanel
  -> Employee B clicks "Request Share"
  -> POST /share-requests { original_file_id, note }
  -> FileShareService creates pending request
  -> Employee A sees notification in their file list
  -> Employee A approves with contribution_pct = 40%
  -> FileShareService clones file record to Employee B's submission
     with owner_contribution_pct = 40%
```

### Why This Design

Keeps `UploadedFile` model unchanged. The share request is a separate workflow entity with its own lifecycle. Cloning the file record (not the physical file) means storage is efficient -- two `UploadedFile` rows point to the same `storage_key`. The `owner_contribution_pct` field already exists on `UploadedFile` to track this.

---

## Feature 3: Menu/Navigation Restructuring (菜单与导航重构)

### Current State

- `roleAccess.ts` defines flat `WorkspaceModuleLink[]` per role -- no grouping
- `AppShell.tsx` renders all nav links in a single flat list under one "导航" header
- Admin has 13 links, HRBP has 9 -- already getting long

### Architecture Changes

**Modified: `roleAccess.ts`**

```typescript
export interface NavGroup {
  label: string;           // group header: "评估管理", "系统管理", "数据导入"
  modules: WorkspaceModuleLink[];
}

// Replace flat ROLE_MODULES with grouped structure:
const ROLE_NAV_GROUPS: Record<string, NavGroup[]> = {
  admin: [
    {
      label: '评估与审批',
      modules: [
        { title: '员工评估', ... },
        { title: '审批中心', ... },
        { title: '调薪模拟', ... },
      ],
    },
    {
      label: '组织与数据',
      modules: [
        { title: '组织看板', ... },
        { title: '考勤管理', ... },
        { title: '员工档案', ... },
        { title: '导入中心', ... },
      ],
    },
    {
      label: '系统管理',
      modules: [
        { title: '创建周期', ... },
        { title: '平台账号', ... },
        { title: '审计日志', ... },
        { title: 'API Key 管理', ... },
        { title: 'Webhook 管理', ... },
        { title: '飞书配置', ... },
        { title: '账号设置', ... },
      ],
    },
  ],
  // ... hrbp, manager, employee groups
};

// Keep getRoleModules() for backward compat (flatten groups)
// Add new: getRoleNavGroups(role): NavGroup[]
```

**Modified: `AppShell.tsx` sidebar**

```
Before: single "导航" header + flat NavLink list
After:  multiple group headers + NavLink lists per group
```

Rendering pattern:
```tsx
{groups.map(group => (
  <div key={group.label}>
    <div className="nav-group-header">{group.label}</div>
    {group.modules.map(module => (
      <NavLink ...>{module.title}</NavLink>
    ))}
  </div>
))}
```

**Modified: `WorkspacePage`** in `App.tsx`

The workspace page grid also benefits from grouping -- show modules grouped by category instead of a flat grid.

**No backend changes needed.**

### Suggested Grouping

| Group (zh) | Admin | HRBP | Manager |
|------------|-------|------|---------|
| 评估与审批 | 员工评估, 审批中心, 调薪模拟 | 员工评估, 审批中心, 调薪模拟 | 员工评估, 审批中心 |
| 组织与数据 | 组织看板, 考勤管理, 员工档案, 导入中心 | 组织看板, 考勤管理, 员工档案, 导入中心 | 组织看板, 员工档案, 导入中心 |
| 系统管理 | 创建周期, 平台账号, 审计日志, API Key, Webhook, 飞书配置, 账号设置 | 平台账号, 账号设置 | 平台账号, 账号设置 |

Employee role stays flat (only 2 items).

### Why This Design

Pure frontend refactor. The `NavGroup` interface is additive -- the flat `getRoleModules()` function can remain for backward compatibility (flatten all groups). The sidebar change is cosmetic but high-impact for usability as the module count grows.

---

## Feature 4: Salary Eligibility Engine (调薪资格校验引擎)

### Current State

- `SalaryEngine` in `engines/salary_engine.py` computes multipliers and ratios -- pure computation, no eligibility checks
- `SalaryService` orchestrates salary recommendation creation
- No pre-check exists before salary computation begins

### Architecture Changes

**New engine: `engines/eligibility_engine.py`**

This is a **pure computation engine** (no I/O, no DB) -- consistent with the existing engine layer pattern.

```python
@dataclass(frozen=True)
class EligibilityRule:
    code: str           # 'TENURE', 'ATTENDANCE', 'PERFORMANCE', 'DISCIPLINARY'
    label: str
    description: str

@dataclass(frozen=True)
class EligibilityCheckResult:
    rule: EligibilityRule
    passed: bool
    reason: str         # human-readable explanation
    data_available: bool  # False = rule couldn't be checked (missing data)

@dataclass(frozen=True)
class EligibilityVerdict:
    eligible: bool
    results: list[EligibilityCheckResult]
    missing_data_rules: list[str]    # rules that couldn't be evaluated
    exception_allowed: bool          # True if override is possible

class EligibilityEngine:
    """Pure computation: takes employee data dict, returns eligibility verdict."""

    RULES = [
        EligibilityRule('TENURE', '在职时长', '员工需在职满试用期（通常3个月）'),
        EligibilityRule('ATTENDANCE', '出勤达标', '考勤出勤率需达到95%以上'),
        EligibilityRule('PERFORMANCE', '绩效合格', '最近绩效评级不低于"合格"'),
        EligibilityRule('DISCIPLINARY', '无处分记录', '近12个月无纪律处分'),
    ]

    def check(self, employee_data: dict) -> EligibilityVerdict:
        # Pure function: evaluates each rule against provided data
        ...
```

**Key design decision:** The engine receives a flat `dict` of employee attributes (tenure_months, attendance_rate, performance_rating, has_disciplinary_action). The **service** layer is responsible for assembling this dict from multiple DB sources (Employee, AttendanceRecord, etc.).

**New service: `services/eligibility_service.py`**

```python
class EligibilityService:
    def __init__(self, db: Session, *, engine: EligibilityEngine | None = None):
        self.db = db
        self.engine = engine or EligibilityEngine()

    def check_employee_eligibility(self, employee_id: str, cycle_id: str) -> EligibilityVerdict:
        # 1. Load employee from DB
        # 2. Load attendance from AttendanceRecord (latest period)
        # 3. Load performance data (if model exists; otherwise mark as missing)
        # 4. Check disciplinary status (if model exists; otherwise mark as missing)
        # 5. Build data dict
        # 6. Call engine.check(data)
        ...

    def batch_check(self, employee_ids: list[str], cycle_id: str) -> dict[str, EligibilityVerdict]:
        ...
```

**New API: `api/v1/eligibility.py`**

```
GET /employees/{id}/eligibility?cycle_id=...    # single check
GET /eligibility/batch?cycle_id=...&dept=...    # batch check for listing
```

**Access control:** Only `admin`, `hrbp`, `manager` can see eligibility. Employees never see this.

**Frontend integration:**

| Component | Type | Details |
|-----------|------|---------|
| `EligibilityBadge.tsx` | NEW | Small badge: green check / red X / yellow warning (missing data) |
| `EvaluationDetail.tsx` | MODIFY | Show eligibility check results before salary recommendation |
| Employee list page | MODIFY | Optional eligibility column (lazy-loaded) |

**Data dependencies:**

The eligibility engine needs data that may not exist yet:
- **Tenure:** Calculable from `Employee.created_at` or a `hire_date` field (may need to add `hire_date` to Employee model)
- **Attendance:** `AttendanceRecord` model exists, synced from Feishu
- **Performance:** No performance rating model exists. Mark as `data_available: false` until imported
- **Disciplinary:** No model exists. Mark as `data_available: false` until imported

The engine handles missing data gracefully with `data_available: bool` on each rule result. The UI shows which rules couldn't be checked and offers an import path.

### Why This Design

Following the established pattern: engine is pure computation (testable without DB), service orchestrates data assembly, API exposes it. The `dict` input to the engine means it doesn't depend on ORM models -- easy to test with plain dicts. Missing data is a first-class concept, not an error.

---

## Feature 5: Salary Recommendation Display Simplification (调薪建议展示精简)

### Current State

- `SalaryResultCard.tsx` shows only `adjustmentRatio` -- extremely minimal (5 lines of display)
- `EvaluationDetail.tsx` and `MyReview.tsx` embed all salary/evaluation info in a long scrollable page
- No collapsible sections exist

### Architecture Changes

**No backend changes needed.** This is purely a frontend display refactor.

**Modified: `SalaryResultCard.tsx`**

Expand to show two tiers of information:

```
DEFAULT VIEW (always visible):
  - 最终调薪幅度: +8.50%
  - AI等级: Level 4
  - 资格状态: [EligibilityBadge] (from Feature 4)

EXPANDABLE DETAIL (click to show):
  - 当前薪资 / 建议薪资
  - AI乘数 / 认证加成 / 最终系数
  - 引擎解释文本 (explanation field)
  - 审批状态时间线
```

**Implementation pattern:**

```tsx
function SalaryResultCard({ recommendation, eligibility }: Props) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="surface">
      {/* Always visible: key metrics */}
      <SalarySummaryRow ... />

      {/* Toggle button */}
      <button onClick={() => setExpanded(!expanded)}>
        {expanded ? '收起详情' : '展开详情'}
      </button>

      {/* Collapsible detail */}
      {expanded && <SalaryDetailPanel ... />}
    </div>
  );
}
```

**New sub-components (inside `components/evaluation/`):**

| Component | Purpose |
|-----------|---------|
| `SalarySummaryRow.tsx` | Key metrics always visible |
| `SalaryDetailPanel.tsx` | Full breakdown, shown on expand |
| `CollapsibleSection.tsx` | Reusable expand/collapse wrapper |

**Modified pages:**

- `EvaluationDetail.tsx`: Wrap the salary section in `CollapsibleSection`
- `MyReview.tsx`: Same treatment, default collapsed for employee view

### Why This Design

No backend API changes. The `SalaryRecommendation` model already has all needed fields (`current_salary`, `recommended_salary`, `ai_multiplier`, `certification_bonus`, `final_adjustment_ratio`, `explanation`). The frontend just needs to render them in a collapsible layout instead of flat.

---

## Build Order and Dependencies

```
Phase 1: Menu/Navigation Restructuring (Feature 3)
    - Zero backend changes, pure frontend refactor
    - No dependency on other features
    - Improves DX for all subsequent feature work (new pages slot into groups)
    - Risk: LOW

Phase 2: Account-Employee Binding (Feature 1)
    - Small backend addition to existing service
    - New UI section in UserAdmin or standalone page
    - Depends on Phase 1 (new page needs a nav group slot)
    - Risk: LOW

Phase 3: Salary Eligibility Engine (Feature 4)
    - New engine + service + API (isolated, no conflicts)
    - Depends on nothing, but benefits from navigation being done
    - May surface missing data models (hire_date, performance, disciplinary)
    - Risk: MEDIUM (data availability uncertainty)

Phase 4: File Upload Sharing (Feature 2)
    - New model + service + API + frontend components
    - Modifies existing FileService dedup logic (highest risk change)
    - Most complex feature: involves notification-like UX, approval workflow
    - Risk: MEDIUM-HIGH (touches critical upload path)

Phase 5: Salary Display Simplification (Feature 5)
    - Pure frontend, depends on Feature 4's EligibilityBadge
    - Best done last since it's a polish pass on existing UI
    - Risk: LOW
```

### Build Order Rationale

1. **Feature 3 first** because it's zero-risk, zero-backend, and sets up the navigation structure for all new pages/sections.
2. **Feature 1 second** because it's small, well-scoped, and the binding service already exists.
3. **Feature 4 third** because the eligibility engine is isolated (new engine, new service, new API) and doesn't modify existing code. It may reveal missing data models early, giving time to plan imports.
4. **Feature 2 fourth** because it modifies the existing `FileService._check_duplicate()` flow -- the riskiest change. By this point, navigation and binding are stable.
5. **Feature 5 last** because it integrates Feature 4's eligibility badge into the salary display, and it's purely cosmetic/UX.

---

## Cross-Cutting Concerns

### Database Migrations

Features requiring Alembic migrations:
- **Feature 2:** New `file_share_requests` table
- **Feature 4:** Potentially add `hire_date` column to `employees` table

Features with no migration needed:
- **Feature 1:** `User.employee_id` FK already exists
- **Feature 3:** Frontend only
- **Feature 5:** Frontend only

### Access Control Matrix

| Feature | admin | hrbp | manager | employee |
|---------|-------|------|---------|----------|
| Binding management | Full CRUD | Bind own dept | View only | Self-bind only |
| Share requests (create) | Yes | Yes | Yes | Yes |
| Share requests (approve) | All | Own dept | Own team | Own files only |
| Eligibility check | View all | View own dept | View own team | Never visible |
| Salary detail expand | Full | Full | Own team | Own only |

### Notification Patterns

Feature 2 (file sharing) introduces a notification-like pattern that doesn't currently exist in the codebase. Options:

**Recommended: Polling-based approach** (simplest, consistent with current architecture)
- `GET /share-requests/pending` returns count + items
- Frontend polls on interval or checks on page load
- No WebSocket/SSE infrastructure needed

**Deferred: Real-time notifications** (future milestone if needed)
- Would require WebSocket layer (not currently in stack)
- Over-engineering for v1.1 scope

---

## Scalability Considerations

| Concern | v1.1 (current) | Future |
|---------|----------------|--------|
| Eligibility checks | Per-employee on-demand | Batch precompute on cycle start |
| File share requests | Simple status column | Could evolve into general notification system |
| Nav groups | Hardcoded in roleAccess.ts | Could become configurable per-org |
| Binding | Manual + auto via id_card_no | Could integrate with SSO/LDAP |

## Sources

- Direct codebase analysis: all models, services, engines, frontend components
- Existing patterns from `EvaluationEngine`, `SalaryEngine`, `IdentityBindingService`
- Role access patterns from `roleAccess.ts` and `ProtectedRoute` in `App.tsx`
