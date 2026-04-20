# Phase 28: 登录页粒子背景 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-20
**Phase:** 28-particle-background
**Areas discussed:** 实现方式, 视觉风格, 鼠标交互行为, 无障碍降级

---

## 实现方式

### Q1: 粒子背景用三方库还是自写？

| Option | Description | Selected |
|--------|-------------|----------|
| 自写 Canvas | 150-250 行 TS，零依赖，与项目极简风格一致 | ✓ |
| tsParticles 库 | 30KB gzip，配置即用 | |
| particles.js 库 | 老牌但已不维护 | |

**User's choice:** 自写 Canvas
**Notes:** 项目现有前端依赖极少（axios/react/tailwind），单个登录页引入 30KB 库不划算。

### Q2: 粒子背景以什么组件形态提供？

| Option | Description | Selected |
|--------|-------------|----------|
| 独立组件 ParticleBackground | 单文件 common/ParticleBackground.tsx | ✓ |
| hook + 组件双层 | useParticleCanvas 逻辑 / 组件负责 DOM | |
| 内联在 Login.tsx | 不抽组件 | |

**User's choice:** 独立组件 ParticleBackground

### Q3: Canvas 如何在页面上分层？

| Option | Description | Selected |
|--------|-------------|----------|
| position: fixed 全屏底层 | 脱离文档流，Phase 29 双栏布局自然兼容 | ✓ |
| position: absolute 页内底层 | 与登录 main 容器共滚动 | |
| CSS 背景 | 非 Canvas 方案 | |

**User's choice:** position: fixed 全屏底层

---

## 视觉风格

### Q4: 粒子主色如何选？

| Option | Description | Selected |
|--------|-------------|----------|
| 主色 #1456F0 低透明度 | 与登录按钮/链接同色系，品牌识别度高 | ✓ |
| 中性淡火银灰 | rgba(30,41,59,0.3) 低调 | |
| 蓝→青渐变 | 多色随机 | |

**User's choice:** 主色 #1456F0 低透明度

### Q5: 粒子总数怎么确定？

| Option | Description | Selected |
|--------|-------------|----------|
| 按面积自适应 | 15000 px/粒子基线，cap 150 | ✓ |
| 固定 80 | 宽屏稀疏 | |
| 固定 120 | 中等安全值 | |

**User's choice:** 按面积自适应

### Q6: 粒子之间的连线如何呈现？

| Option | Description | Selected |
|--------|-------------|----------|
| 距离阈值 120px + 透明度衰减 | 行业标准观感 | ✓ |
| 完全距离依赖无阈值 | O(n²) 全连 | |
| 无连线 | 仅粒子浮动 | |

**Initial selection:** 无连线（被 Claude flag 违反 Success Criteria #1）
**Final choice after clarification:** 距离阈值 120px + 透明度衰减
**Notes:** 初选违反 ROADMAP.md Success Criteria #1「粒子间有连线效果」，用户修正后采纳推荐方案。

---

## 鼠标交互行为

### Q7: 鼠标移动时粒子如何反应？

| Option | Description | Selected |
|--------|-------------|----------|
| 排斥 | 粒子被鼠标推开 | ✓ |
| 吸引 | 粒子聚向鼠标 | |
| 仅鼠标附近画额外连线 | 粒子位置不变 | |
| 吸引 + 点击炸开 | 超出本期需求 | |

**User's choice:** 排斥（鼠标推开粒子）

### Q8: 交互光环半径多大？

| Option | Description | Selected |
|--------|-------------|----------|
| 120px | 中等强度，视觉节奏与连线阈值一致 | ✓ |
| 80px | 小而精 | |
| 180px | 大范围 | |

**User's choice:** 120px

### Q9: 移动端没有鼠标，如何处理？

| Option | Description | Selected |
|--------|-------------|----------|
| 关闭交互，仅粒子浮动 | pointer: coarse 检测触屏 | ✓ |
| touchmove 模拟鼠标 | 触点位移触发排斥 | |
| 禁用整个 Canvas | 触屏不渲染 | |

**User's choice:** 关闭交互，仅保留粒子浮动

---

## 无障碍降级

### Q10: prefers-reduced-motion: reduce 触发时的行为？

| Option | Description | Selected |
|--------|-------------|----------|
| 完全不挂载 Canvas | 组件 return null，纯色背景 | ✓ |
| 渲染静态粒子快照 | 画一帧后停止 | |
| 动画帧率降至 10fps | 慢动仍违反规范 | |

**User's choice:** 完全不挂载 Canvas

### Q11: HiDPI（Retina）清晰策略？

| Option | Description | Selected |
|--------|-------------|----------|
| Canvas 按 DPR 放大 + CSS 缩回 | 行业标准，清晰 | ✓ |
| 不动默认 1x | Retina 模糊 | |
| 固定 2x | 忽略实际 DPR | |

**User's choice:** Canvas 按 DPR 放大 + CSS 缩回

### Q12: 标签页隐藏时动画行为？

| Option | Description | Selected |
|--------|-------------|----------|
| visibilitychange 暂停 | 取消 rAF，省 CPU/电量 | ✓ |
| 不处理，持续动画 | 管理简单但浪费 | |

**User's choice:** visibilitychange 暂停

---

## Claude's Discretion

讨论中用户未明确指定、交由 Claude 判断的细节：

- 粒子单体尺寸（建议 1.5–3px 随机半径）
- 粒子初速度区间与边界策略（建议反弹或环绕，保证粒子稳定分布）
- 排斥光环内的具体位移公式（方向向量 × 距离反比，不超过一个常量 cap）
- 是否做初次挂载淡入

## Deferred Ideas

- 粒子背景跨页面复用（本期只登录页）
- 鼠标点击粒子炸开特效
- 深色模式配色
- 低端设备帧率自适应降级
