# Requirements: Milestone v1.1 体验优化与业务规则完善

**Created:** 2026-03-31
**Milestone:** v1.1

---

## 账号绑定 (BIND)

- [x] **BIND-01**: 管理员可在用户管理页面将用户账号与员工信息手动绑定/解绑
- [x] **BIND-02**: 员工可在个人设置页面通过身份证号自助绑定自己的员工信息
- [x] **BIND-03**: 绑定冲突时（员工已被其他账号绑定）系统阻止操作并提示当前绑定方

## 文件共享 (SHARE)

- [ ] **SHARE-01**: 上传与他人已有文件内容相同的文件时，系统弹出警告但允许继续上传
- [ ] **SHARE-02**: 上传重复文件后，系统自动向原始上传者发起共享申请
- [ ] **SHARE-03**: 原始上传者可在通知列表中审批或拒绝共享申请
- [ ] **SHARE-04**: 共享申请包含贡献比例字段，原始上传者可修改后审批
- [ ] **SHARE-05**: 共享申请超过 72 小时未处理自动标记为超时（不自动审批）

## 菜单导航 (NAV)

- [ ] **NAV-01**: 侧边栏按功能类别分组展示（如：运营管理、系统设置、数据分析）
- [ ] **NAV-02**: 分组支持折叠/展开，保持用户上次展开状态
- [ ] **NAV-03**: 各角色（admin/hrbp/manager/employee）看到的分组和菜单项按权限过滤

## 调薪资格 (ELIG)

- [x] **ELIG-01**: 系统自动检查员工是否入职满 6 个月（基于 hire_date）
- [x] **ELIG-02**: 系统自动检查距上次调薪（含转正调薪、专项调薪）是否满 6 个月（系统记录 + 导入历史）
- [x] **ELIG-03**: 系统自动检查员工年度绩效是否为 C 级及以下（绩效数据支持 Excel 批量导入、飞书多维表格同步、管理端手动录入三种来源）
- [x] **ELIG-04**: 系统自动检查员工年度非法定假期累计是否超过 30 天（排除产假等法定假期，请假数据支持 Excel 导入和飞书多维表格同步）
- [ ] **ELIG-05**: 资格校验结果仅在 HR/主管/管理端显示，员工端不可见
- [ ] **ELIG-06**: HR 可批量查看某部门/全公司的员工调薪资格状态
- [ ] **ELIG-07**: 不符合资格但有特殊情况的员工，部门可提交特殊申请（经 HR 和管理层审批）
- [x] **ELIG-08**: 缺失数据源时（如绩效未导入），资格状态显示"数据缺失"而非直接判定不合格
- [x] **ELIG-09**: 调薪资格所需数据（绩效等级、调薪历史、入职日期、请假天数）支持三种导入通道：Excel 批量导入、飞书多维表格同步、管理端手动录入

## 多模态视觉评估 (VISION)

- [ ] **VISION-01**: PPT 文件中的图片（图表、设计稿、截图等）提取后通过视觉模型进行内容理解和质量评估，而非仅提取文字
- [ ] **VISION-02**: 独立上传的图片文件（PNG/JPG 等）通过视觉模型进行作品质量评估（设计作品、数据可视化、界面截图等）
- [ ] **VISION-03**: 视觉评估结果以结构化 JSON 输出（图片描述、质量评级、与 AI 能力维度的关联度），纳入整体评分计算
- [ ] **VISION-04**: 视觉评估支持批量处理（一次提交中多个图片文件），单个文件评估失败不影响其余文件

## 调薪展示 (DISP)

- [ ] **DISP-01**: 调薪建议页面默认仅展示关键摘要（考勤概况 + 调薪资格状态 + AI 评分）
- [ ] **DISP-02**: 详细数据（维度明细、评分解释、调薪计算过程）通过展开按钮查看
- [ ] **DISP-03**: 调薪资格状态以徽章形式展示（合格/不合格/数据缺失），可展开查看 4 条规则的逐条判定结果

---

## Future Requirements (deferred)

- 拖拽排序菜单
- SSO/LDAP 账号集成
- 可配置的资格规则 UI（当前 4 条规则硬编码，仅阈值外部化）
- 实时 WebSocket 通知（当前使用页面加载时轮询）
- 完整绩效管理模块（当前仅导入绩效等级）

## Out of Scope

- 绩效管理全流程（仅导入绩效等级供资格判定使用）
- 调薪资格规则动态配置界面
- 文件共享自动审批
- 员工端查看调薪资格

---

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| NAV-01 | Phase 11 | Pending |
| NAV-02 | Phase 11 | Pending |
| NAV-03 | Phase 11 | Pending |
| BIND-01 | Phase 12 | Complete |
| BIND-02 | Phase 12 | Complete |
| BIND-03 | Phase 12 | Complete |
| ELIG-01 | Phase 13 | Complete |
| ELIG-02 | Phase 13 | Complete |
| ELIG-03 | Phase 13 | Complete |
| ELIG-04 | Phase 13 | Complete |
| ELIG-08 | Phase 13 | Complete |
| ELIG-09 | Phase 13 | Complete |
| ELIG-05 | Phase 14 | Pending |
| ELIG-06 | Phase 14 | Pending |
| ELIG-07 | Phase 14 | Pending |
| VISION-01 | Phase 15 | Pending |
| VISION-02 | Phase 15 | Pending |
| VISION-03 | Phase 15 | Pending |
| VISION-04 | Phase 15 | Pending |
| SHARE-01 | Phase 16 | Pending |
| SHARE-02 | Phase 16 | Pending |
| SHARE-03 | Phase 16 | Pending |
| SHARE-04 | Phase 16 | Pending |
| SHARE-05 | Phase 16 | Pending |
| DISP-01 | Phase 17 | Pending |
| DISP-02 | Phase 17 | Pending |
| DISP-03 | Phase 17 | Pending |
