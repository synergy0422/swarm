# AI Swarm - tmux 多 Agent 协作系统

## What This Is

基于 tmux 的多 AI Agent 协作系统。多个 AI Agent 在 tmux 会话中并行工作，通过 `capture-pane`（感知）、`send-keys`（控制）+ 共享状态文件（协调）实现蜂群协作。Master 负责任务分配、去重（locks）和救援卡点，Worker 专注于执行任务。

## Core Value

**多 Agent 并行推进，Master 协调去重，减少人作为瓶颈**。自动处理等待/确认类卡点（对危险命令保守，默认不自动确认）。

## Requirements

### Validated

**v1.6 - 长期可维护性 + 流程闭环 (Shipped 2026-02-03)**

- [x] **CFGN-01**: 统一配置入口 — _config.sh 管理 SESSION_NAME/SWARM_STATE_DIR/WORKERS/LOG_LEVEL
- [x] **CFGN-02**: 所有脚本统一读取配置 — _common.sh source _config.sh
- [x] **WRAP-01**: 任务流程包装脚本 — lock → START → execute → DONE/ERROR → release
- [x] **WRAP-02**: 失败场景处理 — SKIP/WAIT 状态，锁释放机制
- [x] **CHK-01**: 一键自检脚本 — tmux/脚本/配置/状态目录检查
- [x] **DOCS-03**: 更新 README — 导航链接到 MAINTENANCE.md/SCRIPTS.md/CHANGELOG.md
- [x] **DOCS-04**: 创建 docs/MAINTENANCE.md — 环境恢复、故障排查、紧急流程、维护清单
- [x] **DOCS-05**: 创建 docs/SCRIPTS.md — 完整脚本索引 (用途/参数/示例)
- [x] **DOCS-06**: 创建 CHANGELOG.md — v1.0-v1.6 变更摘要

**v1.7 - 5 窗格布局 + Codex (Shipped 2026-02-03)**

- [x] **LAYOUT-01**: 5 窗格布局脚本 — `scripts/swarm_layout_5.sh` (左侧 master/codex，右侧 3 workers)
- [x] **LAYOUT-02**: 文档更新 — README.md 和 docs/SCRIPTS.md 新增布局说明

**v1.5 - 状态广播闭环 + 自动救援 + 维护性改进 (Shipped 2026-02-02)**

- [x] **AUTO-01**: Worker 状态广播脚本 — START/DONE/ERROR/WAIT 自动记录
- [x] **AUTO-02**: 状态记录格式 — JSON Lines (task_id, status, worker, timestamp)
- [x] **AUTO-03**: 自动触发机制 — Worker 收到任务/完成任务/遇到错误时自动记录
- [x] **RESC-01**: 自动救援脚本 — 检测 [y/n]/Press Enter → 自动 send-keys Enter
- [x] **RESC-02**: 模式检测 — 识别 confirm, continue, proceed 等确认提示
- [x] **RESC-03**: 30s 冷却机制 — 同一窗口 30s 内不重复确认
- [x] **RESC-04**: 危险命令黑名单 — 检测 rm -rf, DROP 等立即告警不自动确认
- [x] **DOCS-01**: `scripts/_common.sh` — 统一 SWARM_STATE_DIR / SESSION / 输出格式
- [x] **DOCS-02**: `CONTRIBUTING.md` — 脚本规范、测试规范

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

**v1.4 - 共享状态与任务锁 (Shipped 2026-02-02)**

- [x] **STATUS-01**: 状态记录脚本 (`swarm_status_log.sh append/tail/query`)
- [x] **STATUS-02**: status.log 格式规范（JSON Lines）
- [x] **LOCK-01**: 任务锁脚本 (`swarm_lock.sh acquire/release/check/list`)
- [x] **LOCK-02**: 锁原子获取机制（O_CREAT|O_EXCL）
- [x] **LOCK-03**: 锁释放与验证（严格 owner 验证）

### Active

_(No active requirements — start /gsd:new-milestone for v1.8)_

### Out of Scope

- **危险命令自动执行** — rm -rf、DROP TABLE 等需人工确认
- **跨网络分布式协作** — 暂不支持 SSH 远程控制（预留接口）
- **图形界面操作** — 纯终端工具
- **实时交互场景** — 需要人工实时响应的场景
- **修改 swarm/*.py** — v1.7 仅新增脚本，不改 Python 代码

## Current Milestone: v1.8 诊断快照

**Goal:** 一键采集 tmux swarm 运行状态，输出到时间戳目录用于诊断

**Target features:**
- `scripts/swarm_snapshot.sh` — 诊断快照脚本
  - tmux 结构信息（sessions/windows/panes）
  - 每个 pane 的最近 N 行输出（默认 50，可配置）
  - 状态文件（`$SWARM_STATE_DIR/status.log`）
  - 锁目录列表（`$SWARM_STATE_DIR/locks/`）
  - 脚本版本信息（git short SHA）
  - 只读操作，不修改任何状态文件
- README.md — 新增"诊断快照"使用说明
- docs/SCRIPTS.md — 增加 swarm_snapshot.sh 文档

## Context

**Reference Implementation:** `/home/user/group/ai_swarm_phase2/`

**Design Document:** `/home/user/group/AI蜂群协作-tmux多Agent协作系统.md`

**Milestone Archives:** `.planning/milestones/`

**Existing Scripts:**
- `run_claude_swarm.sh` — 根目录，4 独立窗口
- `scripts/*.sh` — scripts/ 目录，配置/通信/任务管理等

## Constraints

- **环境**: 同机 Linux/tmux（WSL 或服务器）
- **依赖最小化**: 仅使用 tmux 原生命令（无第三方依赖）
- **兼容性**: 复用 `_config.sh`/`_common.sh` 配置系统
- **安全**: 危险命令需白名单，默认不自动确认
- **代码限制**: 不修改 `swarm/*.py` 文件

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
| _common.sh 优先 | Foundational config needed by all scripts | ✅ Validated |
| Auto-Rescue 后执行 | Uses shared config for logging | ✅ Validated |
| Worker-only 自动救援 | Master window excluded from auto-confirm | ✅ Validated |
| _config.sh 统一配置 | Single source of truth for configuration | ✅ Validated |
| SWARM_NO_CONFIG=1 | Graceful degradation for testing | ✅ Validated |
| log_debug conditional | Debug logging without performance impact | ✅ Validated |
| task_wrap 原子锁 | Prevents duplicate task execution | ✅ Validated |
| 5-step emergency procedure | 备份 → 优雅停 → 强杀 → 清锁 → 复验 | ✅ Documented |
| scripts/ directory | Consistent with other swarm scripts | ✅ Validated |
| 5-pane single window | Left: master/codex, Right: 3 workers | ✅ Validated |

---

*Last updated: 2026-02-03 after v1.7 milestone complete*
