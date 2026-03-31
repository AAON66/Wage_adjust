# Roadmap: 公司综合调薪工具 (Enterprise Salary Adjustment Platform)

## Milestones

- ✅ **v1.0 MVP** - Phases 1-10 (shipped 2026-03-30)
- 🚧 **v1.1 体验优化与业务规则完善** - Phases 11-17 (in progress)

## Phases

<details>
<summary>v1.0 MVP (Phases 1-10) - SHIPPED 2026-03-30</summary>

- [x] **Phase 1: Security Hardening and Schema Integrity** - Fix production-blocking security vulnerabilities and establish Alembic as the sole migration path (completed 2026-03-26)
- [x] **Phase 2: Evaluation Pipeline Integrity** - Make AI evaluations trustworthy, explainable, and auditable end-to-end (completed 2026-03-31)
- [x] **Phase 3: Approval Workflow Correctness** - Fix race conditions and history-reset bugs; complete reviewer UI (completed 2026-03-31)
- [x] **Phase 4: Audit Log Wiring** - Wire AuditLog into every service mutation so every decision is traceable (completed 2026-03-31)
- [x] **Phase 5: Document Deduplication and Multi-Author** - Prevent duplicate uploads and support shared project attribution (completed 2026-03-31)
- [x] **Phase 6: Batch Import Reliability** - Make bulk employee import idempotent with clear per-row error reporting (completed 2026-03-31)
- [x] **Phase 7: Dashboard and Cache Layer** - Complete all dashboard charts with SQL aggregation and Redis caching (completed 2026-03-31)
- [x] **Phase 8: Employee Self-Service UI** - Give employees visibility into their evaluation status and results (completed 2026-03-31)
- [x] **Phase 9: Feishu Attendance Integration** - Sync attendance data from Feishu for use during salary review (completed 2026-03-31)
- [x] **Phase 10: External API Hardening** - Validate and harden the public REST API for external HR system integration (completed 2026-03-31)

</details>

### v1.1 体验优化与业务规则完善

- [ ] **Phase 11: Menu & Navigation Restructuring** - 侧边栏按功能分组、折叠记忆、角色权限过滤
- [ ] **Phase 12: Account-Employee Binding** - 管理员手动绑定/解绑、员工自助绑定、冲突检测
- [ ] **Phase 13: Eligibility Engine & Data Layer** - 调薪资格 4 条规则引擎、数据缺失处理、三通道导入
- [ ] **Phase 14: Eligibility Visibility & Overrides** - 资格结果权限控制、批量查看、特殊申请审批
- [ ] **Phase 15: Multimodal Vision Evaluation** - PPT 图片提取视觉评估、独立图片评估、结构化输出
- [ ] **Phase 16: File Sharing Workflow** - 重复上传警告、共享申请、审批/拒绝、贡献比例、超时标记
- [ ] **Phase 17: Salary Display Simplification** - 调薪建议摘要优先、展开详情、资格徽章集成

## Phase Details

### Phase 11: Menu & Navigation Restructuring
**Goal**: 用户在侧边栏看到按功能类别分组的菜单，分组可折叠并记住状态，不同角色看到不同的菜单结构
**Depends on**: Nothing (first phase of v1.1)
**Requirements**: NAV-01, NAV-02, NAV-03
**Success Criteria** (what must be TRUE):
  1. 侧边栏菜单项按功能类别分组展示（如运营管理、系统设置、数据分析），而非扁平列表
  2. 用户可折叠/展开分组，刷新页面后保持上次的展开状态
  3. admin 角色可见全部分组和菜单项，employee 角色仅可见与自身相关的分组和菜单项
**Plans**: TBD
**UI hint**: yes

### Phase 12: Account-Employee Binding
**Goal**: 管理员可在后台将用户账号与员工信息绑定/解绑，员工可自助绑定，系统阻止冲突绑定
**Depends on**: Phase 11 (nav slots for binding pages)
**Requirements**: BIND-01, BIND-02, BIND-03
**Success Criteria** (what must be TRUE):
  1. 管理员可在用户管理页面选择一个用户和一个员工进行绑定，也可解除已有绑定
  2. 员工可在个人设置页面输入身份证号完成自助绑定
  3. 当目标员工已被其他账号绑定时，绑定操作被阻止并提示当前绑定方信息
**Plans**: TBD
**UI hint**: yes

### Phase 13: Eligibility Engine & Data Layer
**Goal**: 系统能基于入职时长、上次调薪间隔、绩效等级、非法定假期天数自动判定员工调薪资格，缺失数据显示为"数据缺失"状态，所需数据支持三种导入通道
**Depends on**: Phase 11 (nav structure for new pages)
**Requirements**: ELIG-01, ELIG-02, ELIG-03, ELIG-04, ELIG-08, ELIG-09
**Success Criteria** (what must be TRUE):
  1. 系统自动判定员工入职是否满 6 个月，不满则标记该条规则为"不合格"
  2. 系统自动判定距上次调薪是否满 6 个月（含转正调薪、专项调薪），不满则标记"不合格"
  3. 系统自动判定员工年度绩效是否为 C 级及以下，是则标记"不合格"
  4. 系统自动判定员工年度非法定假期是否超过 30 天，超过则标记"不合格"
  5. 当某条规则所需数据未导入时，该条规则状态显示"数据缺失"而非直接判定不合格
**Plans**: TBD

### Phase 14: Eligibility Visibility & Overrides
**Goal**: 调薪资格校验结果仅对 HR/主管/管理端可见，HR 可批量查看资格状态，不合格员工可提交特殊申请
**Depends on**: Phase 13 (eligibility engine must exist)
**Requirements**: ELIG-05, ELIG-06, ELIG-07
**Success Criteria** (what must be TRUE):
  1. 员工登录后看不到任何调薪资格信息，HR/主管/管理员可以看到
  2. HR 可按部门或全公司维度批量查看员工调薪资格状态列表
  3. 部门可为不合格但有特殊情况的员工提交特殊申请，经 HR 和管理层审批后覆盖资格判定
**Plans**: TBD
**UI hint**: yes

### Phase 15: Multimodal Vision Evaluation
**Goal**: AI 评估可对 PPT 中提取的图片和独立上传的图片进行视觉内容理解和质量评估，结果纳入整体评分
**Depends on**: Nothing (independent; builds on existing evaluation pipeline from v1.0 Phase 2)
**Requirements**: VISION-01, VISION-02, VISION-03, VISION-04
**Success Criteria** (what must be TRUE):
  1. PPT 文件中的图片（图表、截图等）被提取后通过视觉模型进行内容理解，而非仅提取文字
  2. 独立上传的 PNG/JPG 图片通过视觉模型进行作品质量评估
  3. 视觉评估结果以结构化 JSON 输出（图片描述、质量评级、维度关联度），并纳入整体评分计算
  4. 一次提交中多个图片文件可批量处理，单个文件失败不影响其余文件的评估
**Plans**: TBD

### Phase 16: File Sharing Workflow
**Goal**: 上传与他人重复的文件时系统警告但允许继续，并自动发起共享申请，原上传者可审批/拒绝并协商贡献比例
**Depends on**: Nothing (independent; modifies existing FileService from v1.0 Phase 5)
**Requirements**: SHARE-01, SHARE-02, SHARE-03, SHARE-04, SHARE-05
**Success Criteria** (what must be TRUE):
  1. 用户上传与他人已有文件相同内容的文件时，系统弹出警告但允许继续上传
  2. 上传重复文件后，系统自动向原始上传者发起共享申请
  3. 原始上传者可在通知列表中看到共享申请，并可审批或拒绝
  4. 审批共享申请时可修改贡献比例字段
  5. 共享申请超过 72 小时未处理自动标记为超时状态
**Plans**: TBD
**UI hint**: yes

### Phase 17: Salary Display Simplification
**Goal**: 调薪建议页面默认展示关键摘要，详细数据通过展开查看，调薪资格以徽章形式直观展示
**Depends on**: Phase 14 (eligibility badge data)
**Requirements**: DISP-01, DISP-02, DISP-03
**Success Criteria** (what must be TRUE):
  1. 调薪建议页面默认仅展示关键摘要（考勤概况 + 调薪资格状态 + AI 评分），不显示全部详情
  2. 用户点击展开按钮后可查看维度明细、评分解释、调薪计算过程等详细数据
  3. 调薪资格以徽章形式展示（合格/不合格/数据缺失），点击可展开查看 4 条规则的逐条判定结果
**Plans**: TBD
**UI hint**: yes

## Progress

**Execution Order:**
Phases execute in numeric order: 11 -> 12 -> 13 -> 14 -> 15 -> 16 -> 17

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Security Hardening | v1.0 | 5/5 | Complete | 2026-03-26 |
| 2. Evaluation Pipeline | v1.0 | 6/6 | Complete | 2026-03-31 |
| 3. Approval Workflow | v1.0 | 3/3 | Complete | 2026-03-31 |
| 4. Audit Log Wiring | v1.0 | 3/3 | Complete | 2026-03-31 |
| 5. Document Dedup | v1.0 | 4/4 | Complete | 2026-03-31 |
| 6. Batch Import | v1.0 | 3/3 | Complete | 2026-03-31 |
| 7. Dashboard & Cache | v1.0 | 3/3 | Complete | 2026-03-31 |
| 8. Employee Self-Service | v1.0 | 2/2 | Complete | 2026-03-31 |
| 9. Feishu Attendance | v1.0 | 3/3 | Complete | 2026-03-31 |
| 10. External API | v1.0 | 3/3 | Complete | 2026-03-31 |
| 11. Menu & Navigation | v1.1 | 0/TBD | Not started | - |
| 12. Account Binding | v1.1 | 0/TBD | Not started | - |
| 13. Eligibility Engine | v1.1 | 0/TBD | Not started | - |
| 14. Eligibility Visibility | v1.1 | 0/TBD | Not started | - |
| 15. Vision Evaluation | v1.1 | 0/TBD | Not started | - |
| 16. File Sharing | v1.1 | 0/TBD | Not started | - |
| 17. Display Simplification | v1.1 | 0/TBD | Not started | - |
