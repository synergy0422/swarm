# AI Swarm - tmux 多 Agent 协作系统

## What This Is

基于 tmux 的多 AI Agent 协作系统。多个 AI Agent 在 tmux 会话中并行工作，通过 `capture-pane`（感知）、`send-keys`（控制）+ 共享状态文件（协调）实现蜂群协作。Master 负责任务分配、去重（locks）和救援卡点，Worker 专注于执行任务。

## Core Value

**多 Agent 并行推进，Master 协调去重，减少人作为瓶颈**。自动处理等待/确认类卡点（对危险命令保守，默认不自动确认）。

## Requirements

### Validated

**v1.0 MVP - 核心协作能力 (Shipped 2026-01-31)**

- [x] **CORE-01**: tmux 资源发现 — session/window/pane 枚举与选择
- [x] **CORE-02**: 基础能力封装 — capture/read、send/control（含 Enter、C-c 等）
- [x] **CORE-03**: 共享状态目录 — /tmp/ai_swarm/{status.log, tasks.json, locks/, results/}
- [x] **CORE-04**: 协作协议 — 状态广播（START/DONE/WAIT/ERROR/HELP/SKIP）
- [x] **CORE-05**: 任务锁机制 — 避免文件/任务冲突
- [x] **CORE-06**: Master 扫描 — 定期扫描 worker 输出
- [x] **CORE-07**: 自动救援 — 检测 [y/n]、Error/Failed 并进行确认/提醒
- [x] **CORE-08**: CLI 工具 — swarm init/run/master/worker 命令
- [x] **CORE-09**: 一键启动脚本 — tmux 会话初始化 + Master + N Workers
- [x] **CORE-10**: setup.py console_scripts 入口点
- [x] **CORE-11**: 复制 Phase 2 实现 — config.py、task_queue.py、worker_smart.py
- [x] **CORE-12**: 适配新目录 — 修改路径为 /tmp/ai_swarm/
- [x] **CORE-13**: 集成测试 — 207 tests passing

**v1.1 - UAT & CLI 增强 (Shipped 2026-02-01)**

- [x] **CLI-01**: CLI 状态增强 — `swarm status --panes` 查看 tmux 窗口快照
- [x] **CLI-02**: 状态图标 — [ERROR], [DONE], [ ] 状态可视化
- [x] **CLI-03**: UAT 验收测试 — 8/8 测试通过

**v1.2 - Claude Code CLI 多窗口 (Shipped 2026-02-01)**

- [x] **TMUX-01**: tmux 窗口自动创建脚本 — 启动时创建 4 个独立窗口
- [x] **TMUX-02**: Claude CLI 启动命令 — 每个窗口启动 claude CLI
- [x] **TMUX-03**: 窗口命名规范 — master, worker-0, worker-1, worker-2
- [x] **CLAI-01**: Worker 启动配置 — 每个 worker 窗口启动 claude CLI
- [x] **CLAI-02**: Master 启动配置 — master 窗口也启动 Claude CLI
- [x] **CLAI-03**: 启动顺序控制 — 先创建窗口，再依次启动

### Active

**v1.3 - 通信协议（待规划）**

- Master ↔ Worker 消息传递协议
- COMM-01 ~ COMM-04, TEST-03

### Out of Scope

- **危险命令自动执行** — rm -rf、DROP TABLE 等需人工确认
- **跨网络分布式协作** — 暂不支持 SSH 远程控制（预留接口）
- **图形界面操作** — 纯终端工具
- **实时交互场景** — 需要人工实时响应的场景

## Current State

**v1.2 Shipped** — 2026-02-01

- **Codebase:** 4,315 LOC Python, 14 source files, 17 test files
- **Tests:** 207 tests passing (v1.0) + 15 new tests (v1.1)
- **Tech Stack:** Python 3.12+, tmux 3.4, libtmux 0.53.0, requests 2.32.5
- **CLI Commands:** swarm init, up, master, worker, status, status --panes, down
- **Master Coordination:** Scanning, auto-rescue, task dispatch with locks
- **New:** run_claude_swarm.sh — 4 Claude CLI 窗口启动脚本
- **v1.3 Status:** 待规划（通信协议）

## Context

**Reference Implementation:** `/home/user/group/ai_swarm_phase2/`

**Design Document:** `/home/user/group/AI蜂群协作-tmux多Agent协作系统.md`

**Milestone Archive:** `.planning/milestones/v1.0-ROADMAP.md`

## Constraints

- **环境**: 同机 Linux/tmux（WSL 或服务器）
- **依赖最小化**: Python 标准库 + requests（无第三方依赖）
- **兼容性**: 保留 Phase 1/2 的向后兼容
- **安全**: 危险命令需白名单，默认不自动确认

## Key Decisions

| Decision | Rationale | Status |
|----------|-----------|--------|
| 基于文件的通信 | 简单可靠，tmux 环境天然支持 | ✅ Validated |
| 共享目录 /tmp/ai_swarm | 临时目录，进程间共享 | ✅ Validated |
| 状态广播协议 | JSON Lines 格式，易于解析 | ✅ Validated |
| Master-Worker 优先 | 最常用模式，MVP 阶段最实用 | ✅ Validated |
| 危险命令保守 | 防止 AI 误操作导致数据丢失 | ✅ Validated |

---

## Current Milestone: v1.3 Claude Code 4 窗口通信协议

**Goal:** 实现 Master 通过 tmux send-keys/capture-pane 向 Claude CLI 窗口发送任务，Worker 返回状态词

**Design Decisions:**
- **通信模式**: Dispatch — Master 主动分配任务给指定 worker
- **协调方式**: Master decides — Master 控制任务分配逻辑
- **消息格式**: Minimal — 简单文本标记词（[TASK], [DONE], [ERROR]）
- **交互方式**: Marker lines — 使用 tmux pane 标记行区分命令与 Claude 输出

**Target features:**
- **COMM-01**: 消息格式定义 — `[TASK]`, `[DONE]`, `[ERROR]`, `[WAIT]`, `[ACK]` 标记词
- **COMM-02**: Master → Worker 指令发送 — 使用 send-keys 发送带标记的任务描述
- **COMM-03**: Worker → Master 状态回报 — 使用 capture-pane 解析状态标记
- **COMM-04**: 状态标识 — DONE/ERROR/WAIT/HELP 状态词识别与处理
- **COMM-05**: 任务确认机制 — Worker 发送 `[ACK]` 表示收到任务
- **TEST-03**: 通信协议测试 — 验证消息发送/接收/状态回报闭环

---

*Last updated: 2026-02-01 after v1.3 milestone definition*
