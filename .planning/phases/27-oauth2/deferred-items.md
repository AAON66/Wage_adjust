# Phase 27 - Deferred Items

已发现但**不在 Phase 27 Plan 03 scope 内**的问题，记录以便后续 plan 处理。

## 1. backend/tests/test_api/test_auth.py 2 个测试与实现中文化不同步

**发现时间：** Plan 03 Task 3 执行自动化回归时

**失败测试：**
- `backend/tests/test_api/test_auth.py::test_user_can_change_password`
- `backend/tests/test_api/test_auth.py::test_change_password_validates_current_password`

**失败根因：** 测试期望英文 `"Password updated successfully."`，但实现（`backend/app/api/v1/auth.py`）已中文化返回 `"密码修改成功。"`。测试断言字符串未更新。

**是否阻塞 Plan 27-03：** 否。
- Plan 27-03 只修改了 `frontend/src/**` 两个文件（FeishuLoginPanel.tsx 新建，Login.tsx 插入一行），**完全未触碰任何后端 Python 源文件或测试文件**。
- 本失败在 Plan 27-01 / 27-02 执行时同样存在（历史遗留），Phase 26 后端端点新增时未引入。
- 飞书 OAuth 回归（`test_feishu_oauth_integration.py`）4/4 全绿，这是本 Plan 真正关心的回归面。

**Scope boundary：** 按执行规范 SCOPE BOUNDARY，仅自动修复由当前任务改动直接引入的问题。本 failure 先于 Plan 03 存在，属于 out-of-scope，不在 Plan 03 提交中修复。

**建议：** 开一个小型 quick 或 debug GSD 流程，将断言改为 `"密码修改成功。"`（或按项目 i18n 策略调整），一并审查 `test_auth.py` 内其余硬编码英文字符串。

## 2. frontend bundle 超 500kB 警告

**发现时间：** `npm run build` 输出
**警告：** `dist/assets/index-*.js 1,840.66 kB` 超过 500kB 默认阈值。

**是否阻塞 Plan 27-03：** 否。这是**历史积累**的 bundle 大小警告，早于 Phase 27。Plan 27-03 仅新增 ~300 行 tsx 源码，对产物 gzip 后体积影响 < 1%。

**建议：** 在未来独立的前端性能优化 Phase 中处理：按路由做 dynamic import code-split（ProtectedRoute 下的重型 page 单独 chunk），或配置 `build.rollupOptions.output.manualChunks` 分拆 react-router/recharts 等公共依赖。
