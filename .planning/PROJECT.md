# AI Swarm - tmux 多 Agent 协作系统

## What This Is

基于 tmux 的多 AI Agent 协作系统。多个 AI Agent 在 tmux 会话中并行工作，通过 `capture-pane`（感知）、`send-keys`（控制）+ 共享状态文件（协调）实现蜂群协作。Master 负责任务分配、去重（locks）和救援卡点，Worker 专注于执行任务。

## Core Value

**多 Agent 并行推进，Master 协调去重，减少人作为瓶颈**。自动处理等待/确认类卡点（对危险命令保守，默认不自动确认）。

## Requirements

### Validated

(None yet — ship to validate)

### Active

**Phase 1 / MVP - 核心协作能力**

- [ ] **CORE-01**: tmux 资源发现 — session/window/pane 枚举与选择
- [ ] **CORE-02**: 基础能力封装 — capture/read、send/control（含 Enter、C-c 等）
- [ ] **CORE-03**: 共享状态目录 — /tmp/ai_swarm/{status.log, tasks.json, locks/, results/}
- [ ] **CORE-04**: 协作协议 — 状态广播（START/DONE/WAIT/ERROR/HELP/SKIP）
- [ ] **CORE-05**: 任务锁机制 — 避免文件/任务冲突
- [ ] **CORE-06**: Master 扫描 — 定期扫描 worker 输出
- [ ] **CORE-07**: 自动救援 — 检测 [y/n]、Error/Failed 并进行确认/提醒
- [ ] **CORE-08**: CLI 工具 — swarm init/run/master/worker 命令
- [ ] **CORE-09**: 一键启动脚本 — tmux 会话初始化 + Master + N Workers

**Phase 2 - 增强功能（v1 后）**

- [ ] **PIPE-01**: Pipeline 模式 — 任务串行流转（分析→设计→实现→测试）
- [ ] **P2P-01**: P2P 对等模式 — 去中心化协作
- [ ] **HYBRID-01**: 混合模式 — 分组协作 + 统一调度
- [ ] **WEB-01**: Web 状态面板 — Flask 实时监控
- [ ] **SSH-01**: SSH 跨机扩展 — 远程 tmux 控制（预留接口）

### Out of Scope

- **危险命令自动执行** — rm -rf、DROP TABLE 等需人工确认
- **跨网络分布式协作** — 暂不支持 SSH 远程控制（预留接口）
- **图形界面操作** — 纯终端工具
- **实时交互场景** — 需要人工实时响应的场景

## Context

**参考实现**: `/home/user/group/ai_swarm_phase2/` (60% 完成)
- 已完成: config.py、task_queue.py、worker_smart.py、测试套件
- 需补齐: tmux 集成层、master_dispatcher.py、状态协议、自动救援

**设计文档**: `/home/user/group/AI蜂群协作-tmux多Agent协作系统.md`
- 第 1-3 节: 核心思想、技术原理、命令参考 ✅ 已理解
- 第 4 节: 协作协议（状态定义、锁机制）→ 需要实现
- 第 5 节: 架构模式 → MVP 只实现 Master-Worker
- 第 6-10 节: 实战案例、提示词模板、最佳实践、风险、扩展 → MVP 只实现核心功能

**复用策略**:
- Phase 2 代码复制到 `/home/user/AAA/swarm/`
- 补齐 tmux 集成和协作协议
- 整理成统一 CLI 工具

## Constraints

- **环境**: 同机 Linux/tmux（WSL 或服务器）
- **依赖最小化**: Python 标准库 + requests（无第三方依赖）
- **兼容性**: 保留 Phase 1/2 的向后兼容
- **安全**: 危险命令需白名单，默认不自动确认

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| 基于文件的通信 | 简单可靠，tmux 环境天然支持 | ✓ 生产验证 |
| 共享目录 /tmp/ai_swarm | 临时目录，进程间共享 | ✓ 符合文档 |
| 状态广播协议 | JSON Lines 格式，易于解析 | — Pending |
| Master-Worker 优先 | 最常用模式，MVP 阶段最实用 | — Pending |
| 危险命令保守 | 防止 AI 误操作导致数据丢失 | — Pending |

---
*Last updated: 2026-01-31 after MVP scope definition*
