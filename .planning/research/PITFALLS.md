# Pitfalls Research: v1.3 飞书登录与登录页重设计

**Domain:** 企业调薪平台 v1.3 — 飞书 OAuth2 SSO 集成 + 登录页 Canvas 粒子背景重设计
**Researched:** 2026-04-16
**Confidence:** HIGH (基于代码审计 + 飞书开放平台官方文档 + 社区 issue 验证)

> 覆盖 v1.3 两个新增功能的集成陷阱：(1) 飞书 OAuth2 登录叠加现有 JWT 体系，(2) 登录页重设计含 Canvas 粒子背景。v1.0-v1.2 的历史陷阱见之前版本的研究文档。

---

## Critical Pitfalls

### Pitfall 1: 飞书 OAuth2 code 被重复使用 — 竞态窗口

**What goes wrong:**
飞书授权码（`code`）按 OAuth2 规范是一次性的，有效期约 5 分钟。如果后端回调接口未做原子性"已使用"标记，在网络重试或用户双击时，同一个 `code` 可能并发发送给后端两次。两个请求同时查询"code 未被使用"后各自向飞书换取 `user_access_token`，飞书会在第二次请求时返回错误，而第一次请求的绑定逻辑可能已执行一半，导致账号状态不一致。

**Why it happens:**
前端收到飞书回调时会将 `code` 发送给后端。浏览器刷新、网络超时重试、或前端未禁用重复提交都可能触发并发请求。后端如果只做"查询 code 是否使用过"而不是原子性操作，就存在检查-执行间的竞态窗口（TOCTOU）。

**How to avoid:**
1. 使用 Redis `SET NX EX 300`（原子操作）标记 code 已使用：
   ```python
   result = redis.set(f'feishu_oauth_code:{code}', '1', nx=True, ex=300)
   if not result:
       raise HTTPException(status_code=400, detail='授权码已使用，请重新扫码')
   ```
2. 若无 Redis（如开发环境），使用数据库唯一约束：创建 `feishu_oauth_codes` 表，code 加唯一索引，insert 失败则拒绝。
3. 前端回调页面加载后立即禁用重复提交，显示"正在登录…"状态。
4. 无论后端逻辑成功与否，code 标记均保留至过期。

**Warning signs:**
- 飞书接口返回 `99991671: code already used` 错误
- 数据库中出现两条相同 `feishu_open_id` 的绑定记录
- 用户刷新回调页面后出现奇怪的登录状态

**Phase to address:**
飞书 OAuth2 后端接入 phase — callback 接口实现时同步加入，不可后补。

---

### Pitfall 2: state 参数缺失或不校验 — CSRF 绑定劫持

**What goes wrong:**
飞书扫码登录的回调 URL 中包含 `code` 和 `state`。如果后端不校验 `state`，攻击者可以构造一个包含自己飞书 `code` 的回调 URL，诱导已登录的目标用户点击，将目标用户的系统账号绑定到攻击者的飞书身份。在本项目中，这会直接导致攻击者用自己的飞书账号登录后获得目标用户（可能是 HRBP 或管理员）的所有权限。

**Why it happens:**
OAuth2 规范定义 `state` 用于防 CSRF，但很多实现跳过了这一步。尤其是在"首次联调能用就行"心态下，state 校验往往最后才加，或者根本没加。

**How to avoid:**
1. 前端发起扫码前，在 Redis（或 sessionStorage）中生成随机 `state`（UUID）：
   ```typescript
   const state = crypto.randomUUID();
   sessionStorage.setItem('feishu_oauth_state', state);
   // 构造飞书扫码 URL 时带上 state 参数
   ```
2. 飞书回调时，前端将 `state` 随 `code` 一起发送给后端。
3. 后端从 Redis 读取之前存入的 `state`，比对一致后立即删除（防重放）。
4. `state` 不一致时返回 400，不执行任何绑定或登录逻辑。
5. `state` 有效期设为 5 分钟（与 code 一致）。

**Warning signs:**
- 回调接口不接受 `state` 参数
- 后端日志无 `state` 校验相关记录
- 扫码功能"直接用就能跑"但未经安全审查

**Phase to address:**
飞书 OAuth2 后端接入 phase — 与 Pitfall 1 同步实现，不得以"先上功能再加安全"为由推迟。

---

### Pitfall 3: 飞书登录后按工号自动绑定的冲突场景未覆盖

**What goes wrong:**
当前系统的账号-员工绑定逻辑基于身份证号（`id_card_no`）匹配（`IdentityBindingService.auto_bind_user_and_employee`）。v1.3 新增"按工号自动绑定"：飞书用户信息包含 `employee_no`，后端用它在 `employees` 表中查找对应员工，再找到已有的 `User` 账号完成绑定。

未覆盖的冲突场景：
- 场景 A：`employees` 表中该 `employee_no` 不存在（员工未导入系统）
- 场景 B：`employees` 表中该员工已被另一个 `User` 账号绑定（`User.employee_id` 已有值）
- 场景 C：飞书账号已绑定一个员工，但该员工的 `User` 绑定了不同员工
- 场景 D：用同一个飞书账号重复触发绑定流程（重新扫码）

如果这些场景抛出未捕获异常或静默失败，用户会卡在登录流程中，且没有任何有用的提示。

**Why it happens:**
现有 `IdentityBindingService` 设计为通用身份绑定服务，没有为"飞书工号绑定"场景设计的错误分支。开发时容易假设"正常路径"覆盖大多数情况，忽略冲突分支的处理。

**How to avoid:**
1. 飞书 OAuth 回调中，按工号查找员工后，所有绑定冲突均返回明确的错误信息（中文，可直接显示给用户），而不是 500 或通用错误。
2. 设计绑定状态枚举：`BOUND_NEW`（首次绑定成功）、`ALREADY_BOUND`（当前飞书 open_id 已绑定，直接登录）、`EMPLOYEE_NOT_FOUND`（工号不存在）、`EMPLOYEE_TAKEN`（工号已被其他账号绑定）。
3. `ALREADY_BOUND` 场景（最常见的重复登录场景）必须支持：飞书 open_id 已存在 → 直接生成 JWT，不报错。
4. `EMPLOYEE_TAKEN` 场景：提示"该工号已绑定到另一账号，请联系管理员"，不允许覆盖绑定。
5. 新增数据库唯一约束：`users.feishu_open_id` 字段加唯一索引，防止并发绑定。

**Warning signs:**
- 绑定接口对冲突场景统一返回 500 或"系统错误"
- 用户重复扫码后状态不一致
- 管理员后台出现同一员工被多个账号绑定的数据异常

**Phase to address:**
飞书 OAuth2 后端接入 phase — 绑定逻辑设计时必须穷举所有冲突场景，不可假设"正常路径"覆盖所有情况。

---

### Pitfall 4: 飞书扫码 SDK 嵌入的 iframe 同源策略问题

**What goes wrong:**
飞书扫码登录支持两种方式：(1) SDK 方式（在当前页面内嵌 iframe 展示二维码），(2) 重定向方式（跳转到飞书授权页）。选择 SDK 方式时，飞书的 iframe 与宿主页面的通信依赖 `postMessage`。如果宿主页面的 CSP（Content Security Policy）设置了 `frame-src` 或 `default-src`，iframe 会被拦截，二维码无法显示，且不会抛出任何 JavaScript 错误，用户只看到空白区域。

本项目使用 Nginx 作为前端服务器（v1.2 已部署 docker-compose.prod.yml），Nginx 配置中可能存在限制性 CSP 头。

**Why it happens:**
安全加固时设置的 CSP `default-src 'self'` 会阻断所有外部 iframe。飞书扫码 SDK 的 iframe src 为 `https://open.feishu.cn`，不在 `'self'` 范围内。开发环境因无 CSP 限制而正常，生产环境部署后失效。

**How to avoid:**
1. 检查当前 Nginx 配置中的 `Content-Security-Policy` 头（见 `deploy/nginx.conf` 或相关配置文件）。
2. 若使用 SDK 嵌入方式，在 CSP 中添加：
   ```
   frame-src https://open.feishu.cn;
   ```
3. 若使用重定向方式（跳转到飞书授权页），则不需要修改 CSP。重定向方式更简单，推荐优先使用。
4. 在 Nginx 配置变更后，同时在开发（无 CSP）和生产（有 CSP）环境验证二维码显示正常。

**Warning signs:**
- 开发环境扫码正常，生产环境空白
- 浏览器控制台出现 `Refused to frame 'https://open.feishu.cn'` 错误
- 浏览器网络面板中飞书 SDK JS 文件加载但二维码区域为空

**Phase to address:**
飞书 OAuth2 前端集成 phase — 在生产环境首次部署验证时必须检查。

---

### Pitfall 5: 现有 JWT token_version 机制与飞书登录路径的兼容性

**What goes wrong:**
现有系统在账号-员工绑定或解绑时会递增 `User.token_version`，使之前颁发的所有 JWT 失效（见 `auth.py` 的 `refresh` 端点校验）。飞书 OAuth2 登录是一个新的"登录路径"，它同样会生成 JWT。潜在问题：

- 问题 A：飞书绑定逻辑完成后，是否需要递增 `token_version`？若新绑定了飞书身份但旧 JWT 仍有效，旧 JWT 代表的是未绑定飞书的状态，可能导致权限信息不一致。
- 问题 B：管理员从后台解绑某用户的飞书账号后，该用户的现有 JWT 应立即失效。若 `token_version` 未递增，用户持有的旧 token 仍可访问系统。
- 问题 C：`_build_auth_response` 辅助函数（auth.py line 77）生成的 JWT 使用当前 `token_version`，飞书登录必须走同一套 JWT 生成逻辑，不能绕过 `token_version`。

**Why it happens:**
飞书登录是新增代码路径，容易复制粘贴一个简化版 JWT 生成逻辑（不带 `token_version`），或者忘记在飞书绑定/解绑时递增 `token_version`。

**How to avoid:**
1. 飞书登录成功后，必须复用 `_build_auth_response(user, settings)` 生成 JWT，包含 `token_version`。
2. 飞书账号绑定完成时，**不需要**递增 `token_version`（绑定不降低权限，旧 token 仍合法）。
3. 飞书账号解绑时，**必须**递增 `token_version`（类比 v1.1 身份证解绑的处理方式）。
4. 后台管理员主动解绑飞书时，同步调用 `user.token_version += 1` + `db.commit()`。

**Warning signs:**
- 飞书登录返回的 JWT 无 `tv`（token_version）字段
- 解绑飞书后旧 token 刷新成功（应返回 401）
- 飞书登录端点使用了手写的 `create_access_token` 调用，参数与现有登录端点不一致

**Phase to address:**
飞书 OAuth2 后端接入 phase — JWT 生成部分，复用 `_build_auth_response` 不要重写。

---

### Pitfall 6: Canvas 动画在组件卸载时未清理 — rAF 僵尸循环

**What goes wrong:**
登录页粒子背景使用 `requestAnimationFrame` 驱动的 Canvas 动画。如果 `useEffect` 的 cleanup 函数未正确调用 `cancelAnimationFrame`，则：
- 用户登录成功跳转后，粒子动画的 rAF 循环仍在后台持续运行
- 每次 React StrictMode 的双重挂载（开发环境）都会启动一个新的动画循环，导致多个循环并发
- 内存泄漏：Canvas context 持有对 DOM 节点的引用，阻止垃圾回收

**Why it happens:**
Canvas 动画的标准写法是在 `useEffect` 中启动 rAF 递归循环。如果 `useEffect` 的第二个参数是 `[]`（只运行一次），cleanup 函数容易被忽略或写错（使用 rAF 返回的局部变量而非 ref）。

**How to avoid:**
```typescript
const animationRef = useRef<number>(0);
const canvasRef = useRef<HTMLCanvasElement>(null);

useEffect(() => {
  const canvas = canvasRef.current;
  if (!canvas) return;

  function animate() {
    // 绘制粒子
    animationRef.current = requestAnimationFrame(animate);
  }
  animationRef.current = requestAnimationFrame(animate);

  // 清理函数 — 组件卸载时取消 rAF
  return () => {
    cancelAnimationFrame(animationRef.current);
  };
}, []); // 空数组：只启动一次
```
关键点：用 `useRef` 存储 rAF ID（而不是局部变量），cleanup 函数读取 `animationRef.current`。

**Warning signs:**
- Chrome Performance 面板显示登录跳转后 rAF 调用仍在继续
- React DevTools 显示 LoginPage 已卸载但 JS 堆内存未释放
- 开发环境下（StrictMode）动画帧率异常（是正常的两倍或更快）

**Phase to address:**
登录页 Canvas 粒子背景实现 phase — 动画 hook 实现时同步加入，不可事后补充。

---

### Pitfall 7: 飞书开放平台应用配置缺失导致 OAuth 静默失败

**What goes wrong:**
飞书 OAuth2 在以下配置缺失时会静默失败或返回不明错误：
- 回调地址（Redirect URI）未在飞书开放平台"安全设置"中注册 — 飞书直接返回`redirect_uri_mismatch`，浏览器显示空白或飞书错误页
- 所需权限未在"权限与范围"中申请 — `user_access_token` 换取成功但用户信息接口返回权限不足
- 应用未发布版本 / 未经企业管理员审批 — 非应用创建者无法完成 OAuth 登录
- 中国版（feishu.cn）与国际版（larksuite.com）应用混用

**Why it happens:**
飞书开放平台的配置分散在多个页面（安全设置、权限与范围、版本发布），开发者容易只配置一部分。尤其是"发布版本"步骤非常容易被遗漏——应用在开发者自己的账号可以正常扫码，但非开发者员工扫码会失败。

**How to avoid:**
飞书应用配置 checklist（必须全部完成才能开始代码开发）：
1. 安全设置 → 重定向 URL：添加开发环境（`http://localhost:5174/auth/feishu/callback`）和生产环境地址
2. 权限与范围：申请 `contact:user.base:readonly`（获取用户基本信息）和 `contact:user.employee_id:readonly`（获取工号）
3. 版本管理与发布：创建版本并提交企业管理员审批
4. 开发配置：记录 `app_id` 和 `app_secret`，写入 `.env`（`FEISHU_APP_ID`, `FEISHU_APP_SECRET`）
5. 确认应用类型是"企业自建应用"（非"应用商店应用"），中国版域名使用 `https://open.feishu.cn`

**Warning signs:**
- 扫码后飞书 App 提示"应用未发布"
- 回调 URL 返回 `invalid_redirect_uri` 错误
- 用户信息接口返回 `99991663: missing permission`
- 开发者账号可以登录，普通员工无法登录

**Phase to address:**
飞书 OAuth2 前置配置 phase（应作为 v1.3 里程碑的第一步，早于代码开发）。

---

## Moderate Pitfalls

### Pitfall 8: 网页授权（重定向）与扫码登录共用同一后端回调的处理差异

**What goes wrong:**
飞书支持两种 OAuth2 方式：(1) 扫码登录（适合 PC 端，生成二维码让用户用飞书 App 扫码）；(2) 网页授权（适合移动端飞书内打开，自动触发授权，无需扫码）。两种方式都产生 `code`，但流程略有不同：扫码登录的 code 通过飞书 SDK 的 `successCallback` 传递到前端，网页授权的 code 通过重定向 URL query 参数传递。如果后端只设计了一种接收方式，另一种会无声失败。

**How to avoid:**
1. 后端只需要一个 `POST /auth/feishu/callback` 接口，接收 `code` 和 `state`（通过请求体，不依赖 query params）。
2. 前端无论哪种方式，拿到 code 后统一通过 `POST` 请求发给后端。
3. 扫码 SDK 方式：在 `successCallback(code)` 中调用后端接口。
4. 网页授权方式：在回调页面的 `useEffect` 中从 `location.search` 读取 `?code=xxx&state=xxx` 后调用后端接口。

**Phase to address:** 飞书 OAuth2 前端集成 phase

---

### Pitfall 9: 登录页 Canvas 在 HiDPI / Retina 屏幕上粒子模糊

**What goes wrong:**
Canvas 的逻辑尺寸（CSS 像素）和物理像素不一样。在 devicePixelRatio=2 的 Retina 屏幕上，如果只设置 `canvas.style.width/height` 而不同步调整 `canvas.width/height`，所有绘制内容会被拉伸，粒子看起来模糊。

**How to avoid:**
```typescript
const dpr = window.devicePixelRatio || 1;
canvas.width = canvas.offsetWidth * dpr;
canvas.height = canvas.offsetHeight * dpr;
ctx.scale(dpr, dpr);
```
同时监听 `resize` 事件重新设置（用防抖减少频率），在 cleanup 中移除监听器。

**Phase to address:** 登录页 Canvas 粒子背景实现 phase

---

### Pitfall 10: 粒子动画对 `prefers-reduced-motion` 无响应 — 无障碍问题

**What goes wrong:**
前庭障碍或晕动症用户会在操作系统中开启"减弱动态效果"（`prefers-reduced-motion: reduce`）。如果粒子动画无视此设置，强制播放大量移动元素，会导致这部分用户出现不适症状，同时也违反 WCAG 2.1 AA 标准。

**How to avoid:**
```typescript
const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
if (!prefersReduced) {
  // 启动粒子动画
} else {
  // 不启动动画，或只显示静态渐变背景
}
```
此外，Canvas 元素应加 `aria-hidden="true"`，因为粒子是纯装饰性内容。

**Phase to address:** 登录页 Canvas 粒子背景实现 phase

---

### Pitfall 11: 飞书 user_access_token 用于用户信息获取后不需要持久化存储

**What goes wrong:**
飞书 `user_access_token`（通过 code 换取）有效期约 2 小时，且需要通过 `offline_access` scope 申请 refresh token。本项目的飞书登录场景仅需要在登录时获取用户 `open_id` 和 `employee_no` 来完成系统内部绑定和 JWT 生成，之后不需要再调用飞书 API 代表该用户操作。

如果误将飞书 `user_access_token` 存入数据库（类比微信扫码登录的"持久化外部 token"模式），则：
- 需要额外管理 token 刷新逻辑（复杂度++）
- 存在 token 泄露风险（数据库被拖库时）
- 实际上本项目根本不需要这个 token 持久化

**How to avoid:**
飞书 OAuth 回调处理逻辑：
1. 用 code 向飞书换取 `user_access_token`（不存储）
2. 用 `user_access_token` 调用飞书用户信息接口，获取 `open_id` + `employee_no`（一次性使用）
3. 用 `employee_no` 在本系统匹配员工，完成账号绑定（仅存储 `feishu_open_id`，不存储飞书 token）
4. 生成本系统的 JWT，返回给前端
5. 飞书 `user_access_token` 丢弃

存储在 `users` 表的只有 `feishu_open_id`（用于下次扫码时直接匹配），不存储任何飞书 token。

**Phase to address:** 飞书 OAuth2 后端接入 phase — 数据模型设计时明确此决策。

---

### Pitfall 12: 登录页重设计破坏现有 `useAuth` 登录流程

**What goes wrong:**
当前 `LoginPage` 使用 `useAuth().login()` 方法，该方法调用 `loginRequest(payload)` 后立即 `fetchCurrentUser()` 并写入 `AuthContext`。重设计为左右分栏（左侧账号密码 + 右侧飞书）时，容易出现：
- 飞书登录路径绕过 `handleLogin`，直接操作 `localStorage`，不更新 `AuthContext` state，导致页面无法跳转
- 两种登录路径竞态：飞书回调正在处理时，用户又提交了账号密码表单
- 飞书回调页（单独路由）完成后跳转到登录页时，`AuthContext` 已经被 bootstrap 流程读到旧 token，跳转逻辑混乱

**How to avoid:**
1. 在 `useAuth` 中新增 `loginWithFeishu(tokens: TokenPair)` 方法，接收飞书登录后端返回的 tokens，复用 `fetchCurrentUser` + `storeAuthSession` + state 更新逻辑，保证与账号密码登录路径完全一致。
2. 飞书回调页（`/auth/feishu/callback`）调用 `loginWithFeishu` 而不是手动写 localStorage。
3. 两种登录方式在 `LoginPage` 内互斥（飞书扫码展示时账号密码表单 `isSubmitting` 状态标记），防止并发提交。
4. 回调页加载时立即禁用所有交互，避免用户在跳转前操作其他元素。

**Phase to address:** 飞书 OAuth2 前端集成 phase + 登录页重设计 phase（两个 phase 必须协调）。

---

### Pitfall 13: Canvas 粒子数量和动画参数未适配移动端 / 低性能设备

**What goes wrong:**
PC 端流畅运行的粒子数量（如 150 个，连线半径 120px）在低端 Android 手机上可能导致 CPU 占用 80%+，帧率跌至 15fps 以下，整个登录页响应迟滞。尤其是粒子之间的连线计算是 O(n²) 的，100 个粒子 = 9900 次距离计算/帧。

**How to avoid:**
1. 根据 `navigator.hardwareConcurrency`（CPU 核心数）和 `window.devicePixelRatio` 动态调整粒子数：
   - 高性能：`hardwareConcurrency >= 4` → 120 粒子
   - 中性能：`hardwareConcurrency >= 2` → 60 粒子
   - 低性能：其余 → 30 粒子
2. 连线判断前先做区域裁剪（只对同格子或相邻格子的粒子计算距离），避免暴力 O(n²)。
3. 若 `prefers-reduced-motion` 为 reduce，完全不启动动画（见 Pitfall 10）。
4. 测试设备覆盖：至少在 3 年内的中端 Android 手机上验证 30fps 以上。

**Phase to address:** 登录页 Canvas 粒子背景实现 phase

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| 飞书回调用 GET 接收 code（通过 query params） | 前端跳转更简单 | code 暴露在浏览器历史、服务器日志、Referer 头中 | Never — 用 POST 接收 code |
| 跳过 state 校验（"先跑通再加安全"） | 快速联调 | CSRF 绑定劫持漏洞，影响所有用户账号安全 | Never — 必须同步实现 |
| 将飞书 user_access_token 存入 DB | 感觉更完整 | 不必要的安全风险 + 维护成本 | Never — 本项目无需 |
| Canvas 粒子参数硬编码 | 实现简单 | 低端设备性能问题，调整参数需重新部署 | MVP 可以硬编码，但需加 TODO |
| 飞书登录绕过 `useAuth` 直接写 localStorage | 少写代码 | AuthContext 状态不同步，跳转逻辑失效 | Never |
| 扫码 SDK 方式代替重定向方式 | 用户体验更好 | CSP 配置复杂，多一个 iframe 依赖 | 仅在确认 CSP 已正确配置后 |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| 飞书 OAuth2 | 只配置开发环境 redirect URI，忘记配生产环境 | 飞书控制台同时配置开发和生产两个 URI |
| 飞书 OAuth2 | 用 `tenant_access_token` 调用用户信息接口 | 必须用 `user_access_token` 调用 `/authen/v1/user_info` |
| 飞书 OAuth2 | 应用未发布版本，开发者能用但员工不能用 | 发布版本 + 企业管理员审批 |
| 飞书 open_id | 直接用 `union_id` 跨多个飞书应用 | 同一应用内用 `open_id`，跨应用才用 `union_id` |
| Canvas + React | `useEffect` cleanup 使用局部变量存 rAF ID | 用 `useRef` 存 rAF ID，cleanup 读取 `.current` |
| Canvas + React | `canvas.width = 100%`（字符串，无效） | 读取 `canvas.offsetWidth` 再赋值给 `canvas.width` |
| AuthContext + 飞书 | 飞书回调直接 `localStorage.setItem('token', ...)` | 调用 `useAuth().loginWithFeishu(tokens)` |
| 现有 FeishuService | 复用 `feishu_service.py` 的 token 方法做 OAuth | 两个功能完全不同：data sync 用 `tenant_access_token`，登录用 `user_access_token` + code 换取 |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| 粒子连线 O(n²) 暴力计算 | 低端设备帧率 < 15fps | 空间分割（格子裁剪）+ 动态减少粒子数 | 粒子数 > 80 且连线距离 > 100px |
| Canvas 未设置 HiDPI 缩放 | Retina 屏粒子模糊 | `canvas.width = offsetWidth * devicePixelRatio` | devicePixelRatio > 1 的设备 |
| window.resize 未防抖 | 调整窗口大小时 CPU 飙升 | resize 处理器加 16ms 防抖 | 用户拖动窗口调整大小时 |
| 飞书 API 未加超时 | 网络差时后端请求挂起 | `httpx.get(..., timeout=10.0)` | 飞书 API 响应超过 30 秒时 |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| 不校验 state 参数 | CSRF 绑定劫持：攻击者将目标账号绑定到自己飞书身份 | 生成随机 state + callback 时验证 + 用后删除 |
| code 不做一次性校验 | 重放攻击：截获 code 多次换取登录态 | Redis SETNX 原子标记 + 飞书接口本身的单次限制 |
| feishu_open_id 无唯一约束 | 并发绑定导致数据不一致 | `users.feishu_open_id` 唯一索引 |
| 飞书回调接口无速率限制 | 暴力请求回调端点 | 复用现有登录 IP 速率限制逻辑 |
| app_secret 写入前端代码 | 飞书应用密钥泄露 | app_secret 只在后端使用，前端只存 app_id |
| 直接将飞书 user_access_token 返回前端 | 前端 token 泄露可直接调飞书 API | 后端只返回系统 JWT，飞书 token 不出后端 |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| 扫码后无加载状态 | 用户不知道是否在处理，反复扫码 | 扫码成功后立即显示"正在验证身份…"全屏蒙层 |
| 工号不存在时只显示"系统错误" | 用户不知道如何处理 | 明确提示"您的工号尚未录入系统，请联系 HR 管理员" |
| 员工已被其他账号绑定时无提示 | 用户无法自助处理 | 提示"该工号已绑定到另一账号，请联系管理员（邮箱：xxx）" |
| 粒子动画加载前有白屏闪烁 | 视觉突兀 | Canvas 背景用 CSS 设置初始渐变色，动画作为增强层叠加 |
| 登录页左右分栏在移动端变成上下堆叠后很高 | 移动端滚动体验差 | 移动端隐藏左侧说明面板，只显示登录表单和飞书按钮 |

---

## "Looks Done But Isn't" Checklist

- [ ] **飞书 code 一次性校验:** Redis SETNX 已实现 — 验证：同一 code 发送两次，第二次返回 400
- [ ] **state CSRF 防护:** state 生成 + 校验 + 用后删除 — 验证：伪造 state 的回调请求返回 400
- [ ] **feishu_open_id 唯一约束:** Alembic 迁移已包含唯一索引 — 验证：`alembic heads` 显示最新迁移
- [ ] **JWT 生成复用 `_build_auth_response`:** 飞书登录返回的 token 包含 `tv` 字段 — 验证：decode JWT payload
- [ ] **飞书解绑递增 token_version:** 解绑后旧 token 刷新返回 401 — 验证：解绑 → 用旧 refresh token 刷新
- [ ] **Canvas rAF cleanup:** 登录跳转后无僵尸动画循环 — 验证：Chrome Performance 面板确认 rAF 停止
- [ ] **prefers-reduced-motion 响应:** 开启减弱动态效果后无粒子动画 — 验证：操作系统设置 + 页面检查
- [ ] **CSP 配置（如使用 SDK 扫码）:** 生产环境 Nginx CSP 包含 `frame-src open.feishu.cn` — 验证：生产环境扫码二维码显示正常
- [ ] **飞书应用发布:** 非开发者员工账号可以完成扫码登录 — 验证：用普通员工账号扫码测试
- [ ] **HiDPI 粒子清晰度:** Retina 屏粒子不模糊 — 验证：devicePixelRatio=2 设备上肉眼观察
- [ ] **AuthContext 一致性:** 飞书登录和密码登录后 `useAuth().user` 内容格式相同 — 验证：console.log 两种登录后的 user 对象

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| code 重放未防护（已上线发现） | MEDIUM | 立即上线 Redis SETNX 补丁 + 审查数据库中异常绑定记录 |
| state 未校验（已上线发现） | HIGH | 立即下线飞书登录功能 → 修复 → 审查所有 feishu_open_id 绑定记录的合法性 |
| Canvas 僵尸 rAF 循环 | LOW | 修复 cleanup + 发布 → 用户刷新页面自动修复 |
| 飞书应用未发布（员工无法登录） | LOW | 飞书控制台创建版本提交审批（等待管理员审批，约 1 工作日） |
| feishu_open_id 无唯一约束（并发绑定） | MEDIUM | 添加 Alembic 迁移 + 清理异常绑定数据（人工审查） |
| AuthContext 状态不同步 | LOW | 修复 `loginWithFeishu` 方法 + 用户重新登录即可 |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| P1: code 重复使用 | 飞书 OAuth2 后端接入 | 同一 code 发两次，第二次 400 |
| P2: state CSRF | 飞书 OAuth2 后端接入 | 伪造 state 的请求 400 |
| P3: 工号绑定冲突场景 | 飞书 OAuth2 后端接入 | 冲突场景各返回明确中文提示 |
| P4: CSP 阻断 iframe | 飞书 OAuth2 前端集成 | 生产环境扫码二维码正常显示 |
| P5: token_version 兼容 | 飞书 OAuth2 后端接入 | JWT payload 含 tv 字段；解绑后旧 token 401 |
| P6: Canvas rAF 泄漏 | 登录页粒子背景实现 | 跳转后 rAF 停止 |
| P7: 飞书平台配置缺失 | 飞书 OAuth2 前置配置 | 普通员工账号可扫码登录 |
| P8: 两种 OAuth 回调差异 | 飞书 OAuth2 前端集成 | 扫码和网页授权均可成功登录 |
| P9: HiDPI 粒子模糊 | 登录页粒子背景实现 | Retina 屏粒子清晰 |
| P10: prefers-reduced-motion | 登录页粒子背景实现 | 减弱动态效果开启时无粒子动画 |
| P11: 飞书 token 持久化 | 飞书 OAuth2 后端接入（数据模型设计） | DB 无飞书 token 字段 |
| P12: LoginPage 破坏 AuthContext | 飞书 OAuth2 前端集成 + 登录页重设计 | 两种登录后 useAuth().user 均正确 |
| P13: 低端设备性能 | 登录页粒子背景实现 | 中端 Android 手机 30fps 以上 |

---

## Recommended Phase Ordering (Based on Pitfall Dependencies)

1. **飞书 OAuth2 前置配置** — P7 是 blocker，平台未配置则无法联调任何代码
2. **飞书 OAuth2 后端接入** — P1/P2/P3/P5/P11 是安全和正确性基础，必须先于前端
3. **飞书 OAuth2 前端集成** — P4/P8/P12 依赖后端接口稳定后再实现
4. **登录页粒子背景实现** — P6/P9/P10/P13 可独立于 OAuth 功能并行或串行开发
5. **登录页重设计整合** — 最后将两个功能合并到统一 UI，验证整体登录页功能

---

## Sources

- [飞书扫码登录文档 — open.feishu.cn](https://open.feishu.cn/document/home/qr-code-scanning-login-for-web-app/introduction) — HIGH confidence
- [飞书 Get user_access_token API](https://open.feishu.cn/document/authentication-management/access-token/get-user-access-token) — HIGH confidence
- [飞书 How to choose token type](https://open.feishu.cn/document/uAjLw4CM/ugTN1YjL4UTN24CO1UjN/trouble-shooting/how-to-choose-which-type-of-token-to-use) — HIGH confidence
- [Feishu OAuth2 不完全符合 OIDC — github.com/goauthentik/authentik/issues/6577](https://github.com/goauthentik/authentik/issues/6577) — MEDIUM confidence
- [飞书扫码登录避坑指南 — CSDN](https://blog.csdn.net/weixin_28049429/article/details/158673318) — MEDIUM confidence
- [飞书 state CSRF 防护 — juejin.cn](https://juejin.cn/post/7501203502665891866) — MEDIUM confidence
- [React useRequestAnimationFrame + cleanup — css-tricks.com](https://css-tricks.com/using-requestanimationframe-with-react-hooks/) — HIGH confidence
- [Canvas 250 particles React vs Canvas — tigerabrodi.blog](https://tigerabrodi.blog/i-animated-250-particles-in-react-and-it-froze-canvas-fixed-it-in-100-lines) — HIGH confidence
- [MDN Canvas Optimization](https://developer.mozilla.org/en-US/docs/Web/API/Canvas_API/Tutorial/Optimizing_canvas) — HIGH confidence
- [React useEffect memory leaks — medium.com/@90mandalchandan](https://medium.com/@90mandalchandan/understanding-and-managing-memory-leaks-in-react-applications-bcfcc353e7a5) — MEDIUM confidence
- [OAuth2 state CSRF attack vector — RFC 6749 Section 10.12](https://www.rfc-editor.org/rfc/rfc6749#section-10.12) — HIGH confidence
- 代码审计：`backend/app/api/v1/auth.py`, `backend/app/services/identity_binding_service.py`, `backend/app/services/feishu_service.py`, `backend/app/models/user.py`, `backend/app/models/employee.py`, `frontend/src/hooks/useAuth.tsx`, `frontend/src/pages/Login.tsx`

---
*Pitfalls research for: 公司综合调薪工具 v1.3 飞书登录与登录页重设计*
*Researched: 2026-04-16*
