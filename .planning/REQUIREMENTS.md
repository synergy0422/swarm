# AI Swarm - tmux 多 Agent 协作系统

## What This Is

基于 tmux 的多 AI Agent 协作系统。多个 AI Agent 在 tmux 会话中并行工作，通过 `capture-pane`（感知）、`send-keys`（控制）+ 共享状态文件（协调）实现蜂群协作。Master 负责任务分配、去重（locks）和救援卡点，Worker 专注于执行任务。

## Core Value

**多 Agent 并行推进，Master 协调去重，减少人作为瓶颈**。自动处理等待/确认类卡点（对危险命令保守，默认不自动确认）。

## Requirements

### Validated

**v1.4 - 共享状态与任务锁 (Shipped 2026-02-02)**

- [x] **STATUS-01**: 状态记录脚本 (`swarm_status_log.sh append/tail/query`)
- [x] **STATUS-02**: status.log 格式规范（JSON Lines）
- [x] **LOCK-01**: 任务锁脚本 (`swarm_lock.sh acquire/release/check/list`)
- [x] **LOCK-02**: 锁原子获取机制（O_CREAT|O_EXCL）
- [x] **LOCK-03**: 锁释放与验证（严格 owner 验证）

**v1.3 - Claude Code 通信协议 (Shipped 2026-02-02)**

- [x] **SCRIPT-01**: `claude_comm.sh` — tmux send-keys / capture-pane 封装脚本
- [x] **SCRIPT-02**: `claude_poll.sh` — 轮询脚本，定期扫描各窗口状态
- [x] **SCRIPT-03**: `claude_status.sh` — 快速检查各窗口状态
- [x] **COMM-01**: 标记词定义 — `[TASK]`, `[DONE]`, `[ERROR]`, `[WAIT]`, `[ACK]`
- [x] **COMM-02**: 任务消息格式 — `[TASK] {task_id} {description}` (单行)
- [x] **COMM-03**: 状态消息格式 — `[DONE|ERROR|WAIT|HELP] {task_id}`
- [x] **SEND-01**: `send <window> <task_id> "<description>"` — 发送任务
- [x] **SEND-02**: 发送前插入 `[TASK]` 标记行
- [x] **POLL-01**: `poll <window> [--timeout N]` — 捕获窗口输出
- [x] **POLL-02**: 识别 `[DONE]`, `[ERROR]`, `[WAIT]`, `[HELP]`, `[ACK]`
- [x] **POLL-03**: 超时参数支持 (默认 30 秒)
- [x] **TEST-01**: 手动验收 — send → ACK → DONE 验证通过

**v1.2 - Claude Code CLI 多窗口 (Shipped 2026-02-01)**

- [x] **TMUX-01**: tmux 窗口自动创建脚本 — 启动时创建 4 个独立窗口
- [x] **TMUX-02**: Claude CLI 启动命令 — 每个窗口启动 claude CLI
- [x] **TMUX-03**: 窗口命名规范 — master, worker-0, worker-1, worker-2
- [x] **CLAI-01**: Worker 启动配置 — 每个 worker 窗口启动 claude CLI
- [x] **CLAI-02**: Master 启动配置 — master 窗口也启动 Claude CLI
- [x] **CLAI-03**: 启动顺序控制 — 先创建窗口，再依次启动

**v1.1 - UAT & CLI 增强 (Shipped 2026-02-01)**

- [x] **CLI-01**: CLI 状态增强 — `swarm status --panes` 查看 tmux 窗口快照
- [x] **CLI-02**: 状态图标 — [ERROR], [DONE], [ ] 状态可视化
- [x] **CLI-03**: UAT 验收测试 — 8/8 测试通过

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

### Active

**v1.5 - 状态广播闭环 + 自动救援 + 维护性改进**

#### 状态广播 (AUTO)

- [ ] **AUTO-01**: Worker 状态广播脚本 — START/DONE/ERROR/WAIT 自动记录
- [ ] **AUTO-02**: 状态记录格式 — JSON Lines (task_id, status, worker, timestamp)
- [ ] **AUTO-03**: 自动触发机制 — Worker 收到任务/完成任务/遇到错误时自动记录

#### 自动救援 (RESC)

- [ ] **RESC-01**: 自动救援脚本 — 检测 [y/n]/Press Enter → 自动 send-keys Enter
- [ ] **RESC-02**: 模式检测 — 识别 confirm, continue, proceed 等确认提示
- [ ] **RESC-03**: 30s 冷却机制 — 同一窗口 30s 内不重复确认
- [ ] **RESC-04**: 危险命令黑名单 — 检测 rm -rf, DROP 等立即告警不自动确认

#### 维护性 (DOCS)

- [ ] **DOCS-01**: `scripts/_common.sh` — 统一 SWARM_STATE_DIR / SESSION / 输出格式
- [ ] **DOCS-02**: `docs/CONTRIBUTING.md` — 脚本规范、测试规范

### Out of Scope

- **危险命令自动执行** — rm -rf、DROP TABLE 等需人工确认
- **跨网络分布式协作** — 暂不支持 SSH 远程控制（预留接口）
- **图形界面操作** — 纯终端工具
- **实时交互场景** — 需要人工实时响应的场景

## Current State

**v1.5 In Progress** — 2026-02-02

- **Milestone:** 状态广播闭环 + 自动救援 + 维护性改进 (Phases 15-17)
- **Focus:** Roadmap created, ready for planning
- **Status:** 3 phases, 9 requirements mapped

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| **v1.5 Active** | | |
| DOCS-01 | Phase 15 | Pending |
| RESC-01 | Phase 16 | Pending |
| RESC-02 | Phase 16 | Pending |
| RESC-03 | Phase 16 | Pending |
| RESC-04 | Phase 16 | Pending |
| AUTO-01 | Phase 17 | Pending |
| AUTO-02 | Phase 17 | Pending |
| AUTO-03 | Phase 17 | Pending |
| DOCS-02 | Phase 17 | Pending |
| **v1.4 Complete** | | |
| STATUS-01 | Phase 12 | ✅ Done |
| STATUS-02 | Phase 12 | ✅ Done |
| LOCK-01 | Phase 13 | ✅ Done |
| LOCK-02 | Phase 13 | ✅ Done |
| LOCK-03 | Phase 13 | ✅ Done |
| **v1.3 Complete** | | |
| SCRIPT-01 | Phase 11 | ✅ Done |
| SCRIPT-02 | Phase 11 | ✅ Done |
| SCRIPT-03 | Phase 11 | ✅ Done |
| COMM-01 | Phase 11 | ✅ Done |
| COMM-02 | Phase 11 | ✅ Done |
| COMM-03 | Phase 11 | ✅ Done |
| SEND-01 | Phase 11 | ✅ Done |
| SEND-02 | Phase 11 | ✅ Done |
| POLL-01 | Phase 11 | ✅ Done |
| POLL-02 | Phase 11 | ✅ Done |
| POLL-03 | Phase 11 | ✅ Done |
| TEST-01 | Phase 11 | ✅ Done |
| **v1.2 Complete** | | |
| TMUX-01 | Phase 10 | ✅ Done |
| TMUX-02 | Phase 10 | ✅ Done |
| TMUX-03 | Phase 10 | ✅ Done |
| CLAI-01 | Phase 10 | ✅ Done |
| CLAI-02 | Phase 10 | ✅ Done |
| CLAI-03 | Phase 10 | ✅ Done |
| **v1.1 Complete** | | |
| CLI-01 | Phase 9 | ✅ Done |
| CLI-02 | Phase 9 | ✅ Done |
| CLI-03 | Phase 9 | ✅ Done |
| **v1.0 Complete** | | |
| CORE-01 | Phase 1-2 | ✅ Done |
| CORE-02 | Phase 2 | ✅ Done |
| CORE-03 | Phase 3 | ✅ Done |
| CORE-04 | Phase 3 | ✅ Done |
| CORE-05 | Phase 4 | ✅ Done |
| CORE-06 | Phase 4 | ✅ Done |
| CORE-07 | Phase 4 | ✅ Done |
| CORE-08 | Phase 5 | ✅ Done |
| CORE-09 | Phase 5 | ✅ Done |
| CORE-10 | Phase 5 | ✅ Done |
| CORE-11 | Phase 5 | ✅ Done |
| CORE-12 | Phase 5 | ✅ Done |
| CORE-13 | Phase 6 | ✅ Done |

## Next Milestone

**v1.5 - 状态广播闭环 + 自动救援 + 维护性改进**

- 3 phases, 9 requirements
- Next action: `/gsd:plan-phase 15`

## Context

**Reference Implementation:** `/home/user/group/ai_swarm_phase2/`

**Design Document:** `/home/user/group/AI蜂群协作-tmux多Agent协作系统.md`

**Milestone Archives:** `.planning/milestones/`

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
| 单行任务发送 | 防止 Claude 误解多行消息 | ✅ Validated |
| send-raw 子命令 | 协议设置消息不加 [TASK] 前缀 | ✅ Validated |
| 行首 marker 匹配 | 避免描述中的 marker 误匹配 | ✅ Validated |
| Python os.open 原子锁 | 平台无关的原子文件创建 | ✅ Validated |
| SWARM_STATE_DIR 环境变量 | 支持自定义状态目录路径 | ✅ Validated |
| mktemp -d 测试隔离 | 防止测试污染真实数据 | ✅ Validated |

---

*Requirements defined: 2026-02-02*
*Roadmap created: 2026-02-02*
*Last updated: 2026-02-02 after v1.5 roadmap creation*
