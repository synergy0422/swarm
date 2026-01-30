# Requirements: AI Swarm

**Defined:** 2026-01-31
**Core Value:** 多 Agent 并行推进，Master 协调去重，减少人作为瓶颈

## v1 Requirements

### tmux 集成层 (CORE)

- [ ] **CORE-01**: tmux 资源发现 — `tmux list-sessions/windows/panes` 封装
- [ ] **CORE-02**: 能力封装 — `capture/read` (capture-pane)、`send/control` (send-keys)

### 共享状态管理 (CORE)

- [ ] **CORE-03**: 共享目录结构 — `/tmp/ai_swarm/{status.log, tasks.json, locks/, results/}`
- [ ] **CORE-04**: 状态广播 — START/DONE/WAIT/ERROR/HELP/SKIP 协议
- [ ] **CORE-05**: 任务锁 — 文件锁机制避免冲突

### Master-Worker 协作 (CORE)

- [ ] **CORE-06**: Master 扫描 — 定期 scan 其他终端输出
- [ ] **CORE-07**: 自动救援 — 检测 `[y/n]`、`[Y/n]`、`确认` 等等待模式
- [ ] **CORE-08**: 错误检测 — 检测 `Error`、`Failed`、`Exception` 等错误模式

### CLI 与交付 (CORE)

- [ ] **CORE-09**: CLI 工具 — `swarm init/run/master/worker` 命令
- [ ] **CORE-10**: 启动脚本 — 一键 tmux 会话初始化 + Master + N Workers

### 现有代码复用 (CORE)

- [ ] **CORE-11**: 复制 Phase 2 实现 — config.py、task_queue.py、worker_smart.py
- [ ] **CORE-12**: 适配新目录 — 修改路径为 /tmp/ai_swarm/
- [ ] **CORE-13**: 集成测试 — 验证完整工作流

## v2 Requirements

### 增强协作模式

- **PIPE-01**: Pipeline 模式 — 任务串行流转（分析→设计→实现→测试）
- **P2P-01**: P2P 对等模式 — 去中心化协作
- **HYBRID-01**: 混合模式 — 分组协作 + 统一调度

### Web 监控

- **WEB-01**: Flask API — 状态端点
- **WEB-02**: 实时面板 — WebSocket/轮询监控
- **WEB-03**: 任务管理 — 增删改查界面

### 调度优化

- **SCHED-01**: 基于负载的任务分配
- **SCHED-02**: 能力感知调度（Worker 擅长领域）
- **SCHED-03**: 成本优化调度

### 扩展能力

- **SSH-01**: SSH 跨机扩展 — tmux over SSH（预留接口）

## Out of Scope

| Feature | Reason |
|---------|--------|
| 危险命令自动执行 | rm -rf、DROP TABLE 等需人工确认 |
| 跨网络分布式协作 | 暂不支持，Phase 2 预留接口 |
| 图形界面 | 纯终端工具 |
| 实时交互场景 | 需要人工实时响应 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| CORE-01 | Phase 1 | Pending |
| CORE-02 | Phase 1 | Pending |
| CORE-03 | Phase 1 | Pending |
| CORE-04 | Phase 1 | Pending |
| CORE-05 | Phase 1 | Pending |
| CORE-06 | Phase 1 | Pending |
| CORE-07 | Phase 1 | Pending |
| CORE-08 | Phase 1 | Pending |
| CORE-09 | Phase 1 | Pending |
| CORE-10 | Phase 1 | Pending |
| CORE-11 | Phase 1 | Pending |
| CORE-12 | Phase 1 | Pending |
| CORE-13 | Phase 1 | Pending |
| PIPE-01 | Phase 2 | Pending |
| P2P-01 | Phase 2 | Pending |
| WEB-01 | Phase 2 | Pending |
| ... | ... | ... |

**Coverage:**
- v1 requirements: 13 total
- v2 requirements: 9 total
- Mapped to phases: 13 (Phase 1)
- Unmapped: 0 ✓

---
*Requirements defined: 2026-01-31*
*Last updated: 2026-01-31 after MVP scope definition*
