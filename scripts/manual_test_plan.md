# QuantFlow 手动测试计划

## 测试环境

- **生产地址**: https://quantflow-two.vercel.app
- **测试账号**: 浏览器注册一个新的（免费账号）
- **测试文件**: `/root/quantflow/test_normal.csv`、`test_minimal.csv`、`test_bad_data.csv`
- **预计耗时**: 20 分钟

---

## 测试 1: 落地页（2 分钟）

### 1.1 无痕窗口打开
打开 Chrome 无痕窗口 → 访问 `https://quantflow-two.vercel.app`

**检查**:
- [ ] 页面 3 秒内完成加载
- [ ] 大标题 "Backtest Any Trading Strategy in 5 Minutes" 可见
- [ ] "Start for Free" 按钮可见且可点击
- [ ] 向下滚动，区块依次淡入（Framer Motion 动画）
- [ ] 策略卡片（MA Crossover / RSI / Bollinger）排列正常
- [ ] 定价卡片（Free / Pro $19 / Quant $49）对齐正常
- [ ] Footer 链接可见

### 1.2 移动端（或用 Chrome DevTools 模拟）
按 `F12` → 点击设备图标（Toggle Device Toolbar）→ 选 iPhone 12 Pro

**检查**:
- [ ] 标题字号自适应，不溢出
- [ ] CTA 按钮堆叠为竖排
- [ ] 策略卡片单列排列
- [ ] 定价卡片单列排列
- [ ] 导航栏是否正常

### 1.3 导航测试
**操作**: 点击 "Start for Free"

**期望**: 跳转到 `/register` 注册页

---

## 测试 2: 注册与登录（3 分钟）

### 2.1 异常输入验证

| 操作 | 期望结果 |
|------|----------|
| 空表单直接点提交 | 表单验证拦截，红色提示 |
| 输 `abc` 到邮箱框 | 提示 "Invalid email" |
| 输 `ab1` 到密码框 | 提示至少 8 位 |
| 输 `abcdefgh` 到密码框 | 提示需要包含数字 |
| 输 `12345678` 到密码框 | 提示需要包含字母 |

**操作**: 依次执行上表每项，记录实际结果。

### 2.2 正常注册

1. 邮箱: `mytest_[当前时间戳]@gmail.com`
2. 密码: `Test1234`
3. Name: `Manual Tester`
4. 点击 Register

**期望**:
- [ ] 请求发出（看 Network 标签）
- [ ] 成功后跳转到 `/dashboard` 页面
- [ ] 侧边栏显示: Dashboard / Backtest / Billing / Settings

### 2.3 登录测试

**操作**: 登出后重新登录

- [ ] 用正确密码登录 → 进入 Dashboard
- [ ] 用错误密码登录 → 显示错误提示（不跳转）

---

## 测试 3: Dashboard（1 分钟）

**操作**: 登录后自动进入

**检查**:
- [ ] 侧边栏 4 个导航项可见
- [ ] 统计卡片显示（Total Backtests / Win Rate / Avg Sharpe / Running Now）
- [ ] "No backtests yet" 空状态显示
- [ ] 点击 "Get started" → 跳转到 `/backtest`
- [ ] 点击 "New Backtest" 按钮 → 同样跳转

---

## 测试 4: 回测配置向导（5 分钟）

### 4.1 Step 1: Ticker 模式

1. 默认是 "Enter Ticker" 标签
2. 输入 `AAPL`
3. 点击日期预设 "1Y"

**检查**:
- [ ] 输入框自动转大写
- [ ] 日期自动填充（start = 1年前, end = 今天）
- [ ] 点击 "Next" → 进入 Step 2

### 4.2 Step 2: 选择策略

**检查**:
- [ ] 3 张策略卡片（MA Crossover / RSI / Bollinger）显示正常
- [ ] 点击 MA Crossover → 绿色边框 + "Selected" 徽章
- [ ] 点击 RSI → 选中切换，上一个取消
- [ ] 点击 "Next" → 进入 Step 3

### 4.3 Step 3: 策略参数

**MA Cross 模式**:
- [ ] Fast Period 滑块: 拖到 5 → 数字变为 5
- [ ] Slow Period 滑块: 拖到 50 → 数字变为 50
- [ ] MA Type 切换: 点 EMA → 按钮高亮切换

**切回 Step 2 → 选 RSI**:
- [ ] 参数表单动态切换为 RSI 参数
- [ ] RSI Period / Oversold / Overbought 三个滑块可见

**切回 Step 2 → 选 Bollinger**:
- [ ] 参数变为 Period + Std Dev

### 4.4 Step 4: 运行设置

- [ ] Initial Capital: 显示默认值 10000
- [ ] Commission: 显示默认值 0.10%
- [ ] Backtest Name: 可输入自定义名称
- [ ] "Free tier: N backtests remaining today" 提示可见
- [ ] Configuration Summary 卡片显示正确

### 4.5 步骤导航

- [ ] 点击 "Back" → 回到 Step 3
- [ ] 点击 "Back" → 回到 Step 2
- [ ] 步骤指示器高亮正确（当前步骤亮绿色，已完成步骤绿色对勾）
- [ ] 点击 "Next" 两次 → 回到 Step 4

### 4.6 CSV 上传模式

切到 Step 1 → 点 "Upload CSV" 标签 → 上传 `/root/quantflow/test_normal.csv`

**检查**:
- [ ] 拖拽区域高亮
- [ ] 上传后显示预览表格（前 5 行）
- [ ] 显示绿色对勾 + "Valid"
- [ ] 列名正确（date/open/high/low/close/volume）

**再上传 `test_bad_data.csv`**:
- [ ] 显示警告（红色 × + "Issues found"）
- [ ] 错误信息可见

---

## 测试 5: 回测执行（2 分钟）

### 5.1 运行回测

在 Step 4 → 点击绿色 "Run Backtest" 按钮

**检查**:
- [ ] 按钮变为 Loading 状态（旋转动画 + "Running Backtest..."）
- [ ] Network 标签显示 POST 请求
- [ ] 完成后自动跳转到 `/results/[id]`

### 5.2 运行途中

**操作**: 回测执行时，观察右侧预览面板

- [ ] 显示 "Running..." 动画
- [ ] 预览图表可见

---

## 测试 6: 结果展示页（3 分钟）

### 6.1 指标卡片

**检查**:
- [ ] 6 张指标卡片排列为 2 列（桌面端）或 3 列
- [ ] Total Return: 正数为绿色，负数为红色
- [ ] 数字有计数动画（从 0 增长到最终值）
- [ ] Max Drawdown 显示负数
- [ ] 与 B&H 基准的对比显示 △ 箭头

### 6.2 图表交互

**Equity Curve 图表**:
- [ ] 图表正常渲染（不是空白）
- [ ] 绿色线 = 策略收益，灰色虚线 = Buy & Hold
- [ ] 图例显示颜色标记
- [ ] 鼠标悬停显示十字准线 + 日期/数值 tooltip
- [ ] 滚轮缩放正常
- [ ] 鼠标拖拽平移正常

**Drawdown 图表**:
- [ ] 红色填充区域可见
- [ ] 最大回撤值在标题显示

### 6.3 策略信息面板

**检查**:
- [ ] 显示 Symbol / Date Range / Strategy / Initial Capital
- [ ] 策略参数以卡片形式展示

### 6.4 交易记录表格

**检查**:
- [ ] 表格有数据（不是空）
- [ ] 列: # / Entry / Exit / Side / Entry $ / Exit $ / Return / P&L
- [ ] 盈利行绿色，亏损行红色
- [ ] Side 列显示 "LONG" 绿色徽章
- [ ] 点击 Return 列表头 → 排序（升序/降序切换）
- [ ] 点击 P&L 列表头 → 同样排序
- [ ] 分页功能（如果超过 20 条交易）

### 6.5 工具栏操作

- [ ] **New** 按钮 → 跳转到 `/backtest`
- [ ] **Share** 按钮 → 显示 "Copied" 或复制链接
- [ ] **Export** 按钮 → 可点击

---

## 测试 7: Billing 页面（1 分钟）

### 7.1 侧边栏导航

点击侧边栏 "Billing"

**检查**:
- [ ] 当前计划显示 "Free"
- [ ] 状态显示 "Inactive"
- [ ] 月付/年付切换滑块可用
- [ ] 切换年付 → 价格更新，显示 "Save 30%" 徽章
- [ ] Pro 卡片有 "Most Popular" 徽章
- [ ] Free 卡片按钮灰显 "Current Plan"

### 7.2 功能对比表

**检查**:
- [ ] 表格显示 10 项功能对比
- [ ] Pro 列绿色高亮
- [ ] 可横向滚动（移动端）

---

## 测试 8: 错误处理（2 分钟）

### 8.1 网络断开

1. 打开 DevTools → Network → 选 "Offline"
2. 点击 "Run Backtest"

**期望**: 显示网络错误提示（不白屏）

### 8.2 直接访问需登录页面

在未登录状态访问 `https://quantflow-two.vercel.app/dashboard`

**期望**: 重定向到登录页

### 8.3 刷新结果页

回测完成后按 `F5` 刷新

**期望**: 数据不丢失（仍然显示之前的回测结果）

---

## 测试 9: 浏览器兼容性（3 分钟）

在第 1 套浏览器完成所有测试后，换浏览器快速过一遍：

### Chrome（主力）
- [ ] 全部功能正常

### Firefox
1. 打开 `https://quantflow-two.vercel.app`
2. 注册一个新账号
3. 跑一次 AAPL + MA Cross
4. 检查: 落地页 / 回测 / 结果页

### 手机浏览器
1. 手机打开 `https://quantflow-two.vercel.app`
2. 注册 → 配置 AAPL + MA Cross → 运行
3. 检查: 图表是否正常显示

---

## 测试 10: 刷新持久化（1 分钟）

1. 在 `/backtest` 页面配置好 Step 1~4 的所有参数
2. 不要点 Run，直接 `F5` 刷新页面

**期望**:
- [ ] 所有参数保留（localStorage 持久化）
- [ ] 步骤位置保留
- [ ] 股票代码保留
- [ ] 策略选择保留
- [ ] 参数滑块值保留

---

## 🐛 Bug 报告模板

发现问题时，按以下格式记录：

```
Bug #: (序号)
页面: (如 /backtest Step 2)
操作: (详细复现步骤)
期望: (应该发生什么)
实际: (实际发生了什么)
截图: (附截图)
严重程度: P0崩溃 / P1功能不可用 / P2体验问题 / P3视觉问题
```

## 📊 测试结果汇总

| 模块 | 通过 | 失败 | 备注 |
|------|------|------|------|
| 1. 落地页 |  |  |  |
| 2. 注册登录 |  |  |  |
| 3. Dashboard |  |  |  |
| 4. 回测配置 |  |  |  |
| 5. 回测执行 |  |  |  |
| 6. 结果展示 |  |  |  |
| 7. Billing |  |  |  |
| 8. 错误处理 |  |  |  |
| 9. 兼容性 |  |  |  |
| 10. 持久化 |  |  |  |

**最终判定**: GREEN / YELLOW / RED
