# Phase 30: 工号前导零修复 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-21
**Phase:** 30-employee-no-leading-zero
**Areas discussed:** 飞书校验, 观测落地, 导入规范化, 模板示例

---

## 飞书校验（EMPNO-03）

| Option | Description | Selected |
|--------|-------------|----------|
| 保存配置时即时校验 | 配置页保存时调用飞书 `list_bitable_fields`，字段非 text 拒绝保存并提示；快失败，HR 不会在同步时才发现 | ✓ |
| 同步运行时验大小写上报 | 保存不验；每次同步开始前读字段元信息，非 text 则同步 sync_log 报错。减少一次 API 调用但故障后知 | |
| 两者都做 | 保存时校验 + 运行时校验。最安全，但飞书 API 调用翻倍 | |

**User's choice:** 保存配置时即时校验（推荐）
**Notes:** 快失败优于故障后知；飞书 API 配额宽松，但减少重复调用更合理。若 HR 事后在飞书改字段类型，需重新保存配置触发校验。

---

## 观测落地（EMPNO-04）

| Option | Description | Selected |
|--------|-------------|----------|
| 结构化日志（stdlib logging warning） | 每次 stripped 匹配命中时 `logger.warning`；项目既有模式，无新依赖 | |
| FeishuSyncLog 新增 `leading_zero_fallback_count` 字段 | 在 FeishuSyncLog 模型上加计数字段；HR 同步日志页直接可见；与 Phase 31 的五类计数器在同一 UI 汇总 | ✓ |
| 新建 MetricEvent 表（通用基础设施） | 更通用的观测表，可扩展到其他场景；scope 偏大 | |

**User's choice:** FeishuSyncLog 新增 leading_zero_fallback_count 字段（推荐）
**Notes:** HR 可视化最优，与 Phase 31 同步日志一致；Alembic 迁移简单（batch_alter_table 添字段）；不做告警只做诊断信号。

---

## 导入规范化（EMPNO-02）

| Option | Description | Selected |
|--------|-------------|----------|
| 严格：拒绝 float/int 主键列 | dtype=str 后仍为非文本则 failed_rows，错误文案要求使用最新模板 | |
| 宽容：静默转 str + 日志 | 照平处理 + logger.warning；HR 体验顺畅但丢零风险被吃掉 | |
| 混合：模板列格式强制 + 报错消息含补救提示 | 拒绝不规范列，但错误消息明确指导「在 Excel 中将该列改为文本格式后重新上传，或重下模板」 | ✓ |

**User's choice:** 混合：模板列格式强制 + 报错消息含补救提示
**Notes:** 失败要可操作而不是把球踢回 HR；补救提示必须点名「改文本列」与「重下模板」两条路径。

---

## 模板示例（EMPNO-01）

| Option | Description | Selected |
|--------|-------------|----------|
| 保持现状 EMP-1001 风格 | 不改示例；仅应用 cell.number_format='@' | |
| 改为 '02651' 风格示例 | 示例直接展示带前导零的数字工号；HR 下载模板就直观看到「工号是文本列且前导零保留」 | ✓ |
| 两行示例（混合 + 数字） | 示例 1 = EMP-1001，示例 2 = 02651；教学价值最高 | |

**User's choice:** 改为 '02651' 风格示例（推荐）
**Notes:** 采用用户原话中的具体工号，回归防御测例；保持示例简洁，不塞两行避免 HR 混淆。

---

## Claude's Discretion

- Pydantic `EmployeeBase.employee_no: str` 已足够约束 JSON API 层，Phase 30 不新增 `field_validator`
- 补救提示具体文案（保持「改文本列」+「重下模板」两点即可）
- 单测用例 mock 数据细节

## Deferred Ideas

- 存量工号批量修补（EMPNO-05 已在 v1.4 kickoff 时明确 defer）
- 通用 MetricEvent 基础设施
- 飞书同步运行时字段类型二次校验（D-02 明确不做）
- 模板下载 HTTP Header 的 UX 提示
