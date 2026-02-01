# Requirements: AI Swarm v1.3 Claude Code 通信协议

**Defined:** 2026-02-01
**Core Value:** 多 Agent 并行推进，Master 协调去重，减少人作为瓶颈

## v1.3 Requirements

### 消息格式定义

- [ ] **COMM-01**: 标记词协议 — 定义 `[TASK]`, `[DONE]`, `[ERROR]`, `[WAIT]`, `[ACK]` 五个核心标记词
- [ ] **COMM-02**: 任务消息格式 — `[TASK] {task_id} {worker_name}\n{description}` 行格式
- [ ] **COMM-03**: 状态消息格式 — 单行 `[STATUS] {task_id} {state}` 或 `[DONE|ERROR|WAIT|HELP]`

### Master → Worker 指令发送

- [ ] **COMM-04**: send-keys 封装 — TmuxSwarmManager 新增 `send_command(window, command)` 方法
- [ ] **COMM-05**: 标记行插入 — 发送任务前先插入 `[TASK]` 标记行
- [ ] **COMM-06**: Worker 定位 — 通过窗口名定位 tmux pane (master, worker-0, worker-1, worker-2)

### Worker → Master 状态回报

- [ ] **COMM-07**: capture-pane 封装 — TmuxSwarmManager 新增 `capture_output(window)` 方法
- [ ] **COMM-08**: 标记词解析 — 从 pane 内容中提取 `[DONE]`, `[ERROR]`, `[WAIT]`, `[HELP]` 状态
- [ ] **COMM-09**: 任务 ID 关联 — 状态回报需包含对应的 task_id

### 任务确认机制

- [ ] **COMM-10**: ACK 响应 — Worker 收到任务后需发送 `[ACK] {task_id}` 确认
- [ ] **COMM-11**: 超时处理 — Master 等待 ACK，超时则重试或标记失败
- [ ] **COMM-12**: 轮询策略 — Master 定期扫描各 worker pane 获取状态

### 错误处理

- [ ] **COMM-13**: 状态词识别 — DONE/ERROR/WAIT/HELP/FAILED 的正则匹配
- [ ] **COMM-14**: 空输出处理 — capture-pane 返回空时的处理逻辑
- [ ] **COMM-15**: tmux 不可用 — tmux 不可用时的优雅降级

## v1.2 Requirements (Validated)

- [x] **TMUX-01**: tmux 窗口自动创建脚本
- [x] **TMUX-02**: 窗口布局配置
- [x] **TMUX-03**: 会话命名规范
- [x] **CLAI-01**: Worker 启动命令
- [x] **CLAI-02**: Master 启动配置
- [x] **CLAI-03**: 启动顺序控制
- [x] **TEST-01**: 窗口可见性验证
- [x] **TEST-02**: 启动脚本测试

## Out of Scope

| Feature | Reason |
|---------|--------|
| Pipeline 模式 | 任务链式依赖，v1.4+ |
| P2P 对等模式 | Worker 间直接通信，v1.4+ |
| Web 状态面板 | 图形界面，超出 tmux 范围 |
| SSH 跨机扩展 | 分布式协作，未来版本 |
| 危险命令自动执行 | 保持保守策略 |
| 后台 Python 任务队列 | 不引入额外进程通信 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| COMM-01 | Phase 11 | Pending |
| COMM-02 | Phase 11 | Pending |
| COMM-03 | Phase 11 | Pending |
| COMM-04 | Phase 11 | Pending |
| COMM-05 | Phase 11 | Pending |
| COMM-06 | Phase 11 | Pending |
| COMM-07 | Phase 11 | Pending |
| COMM-08 | Phase 11 | Pending |
| COMM-09 | Phase 11 | Pending |
| COMM-10 | Phase 11 | Pending |
| COMM-11 | Phase 11 | Pending |
| COMM-12 | Phase 11 | Pending |
| COMM-13 | Phase 11 | Pending |
| COMM-14 | Phase 11 | Pending |
| COMM-15 | Phase 11 | Pending |

**Coverage:**
- v1.3 requirements: 15 total (COMM-01 ~ COMM-15)
- Phase 11 mapped: 15/15
- Unmapped: 0 ✓

---
*Requirements defined: 2026-02-01*
*Last updated: 2026-02-01 after v1.3 milestone definition*
