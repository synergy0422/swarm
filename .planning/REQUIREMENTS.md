# Requirements: AI Swarm v1.3 Claude Code 通信协议

**Defined:** 2026-02-01
**Core Value:** 多 Agent 并行推进，Master 协调去重，减少人作为瓶颈

## v1.3 Requirements

### 脚本工具

- [ ] **SCRIPT-01**: `claude_comm.sh` — tmux send-keys / capture-pane 封装脚本
- [ ] **SCRIPT-02**: `claude_poll.sh` — 轮询脚本，定期扫描各窗口状态
- [ ] **SCRIPT-03**: `claude_status.sh` — 快速检查各窗口状态

### 消息格式

- [ ] **COMM-01**: 标记词定义 — `[TASK]`, `[DONE]`, `[ERROR]`, `[WAIT]`, `[ACK]`
- [ ] **COMM-02**: 任务消息格式 — `[TASK] {task_id}\n{description}`
- [ ] **COMM-03**: 状态消息格式 — `[DONE|ERROR|WAIT|HELP] {task_id}`

### 脚本功能

- [ ] **SEND-01**: `send <window> <task_id> "<description>"` — 发送任务到指定窗口
- [ ] **SEND-02**: 发送前插入 `[TASK]` 标记行
- [ ] **POLL-01**: `poll <window> [--timeout N]` — 捕获窗口输出，解析状态标记
- [ ] **POLL-02**: 识别 `[DONE]`, `[ERROR]`, `[WAIT]`, `[HELP]`, `[ACK]`
- [ ] **POLL-03**: 超时参数支持

### 验收测试

- [ ] **TEST-01**: 手动验收 — 发送任务到 worker-0，验证返回 [ACK] + [DONE]
- [ ] **TEST-02**: 错误场景 — 发送无效任务，验证返回 [ERROR]
- [ ] **TEST-03**: 并发测试 — 向多个 worker 同时发送任务

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
| Python 通信模块 | v1.3 只做外部脚本，不改 core 代码 |
| Master 集成 | 不修改 swarm/master.py |
| Pipeline 模式 | 任务链式依赖，v1.4+ |
| P2P 对等模式 | Worker 间直接通信，v1.4+ |
| Web 状态面板 | 图形界面，超出 tmux 范围 |
| SSH 跨机扩展 | 分布式协作，未来版本 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| SCRIPT-01 | Phase 11 | Pending |
| SCRIPT-02 | Phase 11 | Pending |
| SCRIPT-03 | Phase 11 | Pending |
| COMM-01 | Phase 11 | Pending |
| COMM-02 | Phase 11 | Pending |
| COMM-03 | Phase 11 | Pending |
| SEND-01 | Phase 11 | Pending |
| SEND-02 | Phase 11 | Pending |
| POLL-01 | Phase 11 | Pending |
| POLL-02 | Phase 11 | Pending |
| POLL-03 | Phase 11 | Pending |
| TEST-01 | Phase 11 | Pending |
| TEST-02 | Phase 11 | Pending |
| TEST-03 | Phase 11 | Pending |

**Coverage:**
- v1.3 requirements: 14 total
- Phase 11 mapped: 14/14
- Unmapped: 0 ✓

---
*Requirements defined: 2026-02-01*
*Last updated: 2026-02-01 after constraint correction*
