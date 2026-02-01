# Requirements: AI Swarm v1.2 Claude Code CLI 多窗口

**Defined:** 2026-02-01
**Core Value:** 多 Agent 并行推进，Master 协调去重，减少人作为瓶颈

## v1.2 Requirements

### tmux 窗口管理

- [x] **TMUX-01**: tmux 窗口自动创建脚本 — 启动时创建 4 个独立窗口（master, worker-0, worker-1, worker-2）
- [x] **TMUX-02**: 窗口布局配置 — master 在主窗口，3 个 worker 窗口
- [x] **TMUX-03**: 会话命名规范 — swarm-claude-default

### Claude CLI 启动

- [x] **CLAI-01**: Worker 启动命令 — 每个 worker 窗口启动 claude CLI（使用 claude command）
- [x] **CLAI-02**: Master 启动配置 — master 窗口启动 Claude CLI
- [x] **CLAI-03**: 启动顺序控制 — 先创建窗口，再依次启动各进程

### 验证与测试

- [x] **TEST-01**: 窗口可见性验证 — 进入 tmux 可看到 4 个 Claude CLI 交互窗口
- [x] **TEST-02**: 启动脚本测试 — 脚本执行后正确创建 4 窗口

## v1.3 Requirements (通信协议)

### 简单通信协议

- **COMM-01**: 消息格式定义 — 简单文本协议（行分隔）
- **COMM-02**: Master → Worker 指令发送 — 使用 send-keys 发送任务描述
- **COMM-03**: Worker → Master 状态回报 — 使用 capture-pane 读取输出状态
- **COMM-04**: 状态标识 — DONE、ERROR、WAIT 等状态词识别
- **TEST-03**: 通信协议测试 — 简单的消息发送/接收测试

## v1.1 Requirements (Validated)

- [x] **CLI-01**: CLI 状态增强 — `swarm status --panes` 查看 tmux 窗口快照
- [x] **CLI-02**: 状态图标 — [ERROR], [DONE], [ ] 状态可视化
- [x] **CLI-03**: UAT 验收测试 — 8/8 测试通过

## Out of Scope

| Feature | Reason |
|---------|--------|
| 通信协议 (COMM-01~04) | v1.3 - 独立里程碑 |
| Pipeline 模式 | v1.3 或更新 - 4 窗口启动后 |
| P2P 对等模式 | v1.3 或更新 - 4 窗口启动后 |
| Web 状态面板 | v1.3 或更新 - 4 窗口启动后 |
| SSH 跨机扩展 | 保留接口，未来版本 |
| 危险命令自动执行 | 保持 v1.1 保守策略 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| TMUX-01 | Phase 10 | Complete |
| TMUX-02 | Phase 10 | Complete |
| TMUX-03 | Phase 10 | Complete |
| CLAI-01 | Phase 10 | Complete |
| CLAI-02 | Phase 10 | Complete |
| CLAI-03 | Phase 10 | Complete |
| TEST-01 | Phase 10 | Complete |
| TEST-02 | Phase 10 | Complete |

**v1.2 Coverage:**
- v1.2 requirements: 8 total (TMUX-*, CLAI-*, TEST-01, TEST-02)
- v1.2 completed: 8/8 ✓

**v1.3 Requirements (通信协议):**
- COMM-01 ~ COMM-04, TEST-03 → 独立里程碑

---
*Requirements defined: 2026-02-01*
*Last updated: 2026-02-01 after v1.2 completion*
