# Roadmap: AI Swarm

**Defined:** 2026-01-31
**Core Value:** 多 Agent 并行推进，Master 协调去重，减少人作为瓶颈

## Phase Overview

| # | Phase | Goal | Requirements | Status |
|---|-------|------|--------------|--------|
| 1 | **项目初始化** | 复制 Phase 2 代码，搭建目录结构 | CORE-11, CORE-12 | Complete |
| 2 | **tmux 集成层** | 实现资源发现、capture/send 封装 | CORE-01, CORE-02 | Complete |
| | 3 | **共享状态系统** | 实现状态广播、任务锁机制 | CORE-03, CORE-04, CORE-05 | Complete |
| 4 | **Master 实现** | Master 扫描、自动救援、任务分配 | CORE-06, CORE-07, CORE-08 | Complete |
| 5 | **CLI 与启动脚本** | 统一 CLI 命令，一键启动 | CORE-09, CORE-10 | Complete (gaps closed) |
| 6 | **集成测试** | 验证完整工作流 | CORE-13 | Pending |

## Phase 1: 项目初始化

**Goal:** 复制 Phase 2 代码，搭建 MVP 目录结构

**Requirements:** CORE-11, CORE-12

**Plans:** 1 plan

**Plan list:**
- [ ] 01-PLAN.md — Restructure Phase 2 code into MVP layout, configure paths, verify tests

**Success Criteria:**
1. ✅ `/home/user/AAA/swarm/` 包含 Phase 2 核心文件
2. ✅ 路径修改为 `/tmp/ai_swarm/`
3. ✅ 测试通过（29/29）

**Key Tasks:**
- [ ] 复制 config.py、task_queue.py、worker_smart.py
- [ ] 复制 tests/ 目录
- [ ] 更新路径配置
- [ ] 运行测试验证

## Phase 2: tmux 集成层

**Goal:** 实现 tmux 资源发现、capture/read、send/control 封装

**Requirements:** CORE-01, CORE-02

**Plans:** 1 plan

**Plan list:**
- [x] 02-PLAN.md — TmuxSwarmManager with AgentStatus and AgentPane

**Success Criteria:**
1. ✅ `tmux list-sessions` 封装可用
2. ✅ `tmux list-windows -a` 封装可用
3. ✅ `tmux capture-pane -t <session>:<window> -p` 封装可用
4. ✅ `tmux send-keys -t <session>:<window> "cmd" Enter` 封装可用
5. ✅ 特殊按键支持（C-c、Enter、Escape 等）

**Key Tasks:**
- [x] 创建 `tmux_client.py` 模块
- [x] 实现 `TmuxResource` 类（资源发现）
- [x] 实现 `TmuxCapture` 类（读取终端）
- [x] 实现 `TmuxControl` 类（发送命令）
- [x] 单元测试覆盖

## Phase 3: 共享状态系统

**Goal:** 实现状态广播协议、任务锁机制

**Requirements:** CORE-03, CORE-04, CORE-05

**Plans:** 1 plan

**Plan list:**
- [x] 03-PLAN.md — Status broadcaster and task lock modules with tests

**Success Criteria:**
1. ✅ `/tmp/ai_swarm/` 目录结构正确
2. ✅ 状态日志写入格式正确
3. ✅ 任务锁防止重复执行
4. ✅ 原子写入操作

**Key Tasks:**
- [x] 创建 `status_broadcaster.py` 模块
- [x] 实现 START/DONE/WAIT/ERROR/HELP/SKIP 状态
- [x] 创建 `task_lock.py` 模块（原子文件锁）
- [x] 集成到现有 task_queue.py
- [x] 单元测试覆盖

## Phase 4: Master 实现

**Goal:** 实现 Master 扫描、自动救援、任务分配

**Requirements:** CORE-06, CORE-07, CORE-08

**Plans:** 3 plans in 2 waves

**Plan list:**
- [x] 04-01-PLAN.md — MasterScanner with scan_loop, status reading, lock checking
- [x] 04-02-PLAN.md — AutoRescuer with WAIT pattern detection and conservative auto-confirm
- [x] 04-03-PLAN.md — MasterDispatcher with FIFO dispatch, lock acquisition, ASSIGNED broadcast

**Success Criteria:**
1. Master 定期扫描所有 worker
2. 检测 `[y/n]`、`[Y/n]`、`确认` 等等待模式
3. 检测 `Error`、`Failed`、`Exception` 等错误模式
4. 可配置是否自动确认（默认否）
5. 任务分配到空闲 worker

**Key Tasks:**
- [x] 实现 `master_scanner.py` 模块
- [x] 实现 `auto_rescuer.py` 模块
- [x] 实现 `master_dispatcher.py`
- [x] 集成测试覆盖

## Phase 5: CLI 与启动脚本

**Goal:** 统一 CLI 命令，一键启动 tmux 会话

**Requirements:** CORE-09, CORE-10

**Plans:** 1 plan (+ 2 gap closure plans)

**Plan list:**
- [x] 05-01-PLAN.md — CLI module with init, up, master, worker, status, down commands
- [x] 05-02-PLAN.md — Gap closure: Fix --cluster-id flag position for subcommand usage
- [x] 05-03-PLAN.md — Gap closure: Remove cli import to fix RuntimeWarning

**Success Criteria:**
1. ✅ `swarm init` 初始化环境检查和目录创建
2. ✅ `swarm up` 启动 tmux 会话（master + N workers）
3. ✅ `swarm master` 单独启动 master 进程
4. ✅ `swarm worker --id <n>` 单独启动 worker
5. ✅ `swarm status` 显示会话和 agent 状态
6. ✅ `swarm down` 终止 tmux 会话
7. ✅ setup.py 配置 console_scripts 入口点
8. ✅ README.md 5 行使用说明
9. ✅ `swarm status --cluster-id default` works (gap closed)
10. ✅ `python3 -m swarm.cli` runs without RuntimeWarning (gap closed)

**Key Tasks:**
- [x] 创建 `cli.py` 入口点（argparse 结构）
- [x] 实现 init 命令（依赖检查、目录创建）
- [x] 实现 master/worker 命令（直接导入执行）
- [x] 实现 up 命令（tmux session 编排）
- [x] 实现 status/down 命令（状态查询、会话终止）
- [x] 创建 setup.py（console_scripts）
- [x] 更新 README.md（Usage 部分）
- [x] Gap 05-02: 使用 argparse parents 模式添加 --cluster-id 到所有子命令
- [x] Gap 05-03: 移除 __init__.py 中的 cli 导入

## Phase 6: 集成测试

**Goal:** 验证完整工作流

**Requirements:** CORE-13

**Success Criteria:**
1. ✅ Master + 3 Workers 启动成功
2. ✅ 任务分配正确
3. ✅ 状态广播正常
4. ✅ 自动救援生效（测试模式）
5. ✅ 13 个 v1 需求全部验证通过

**Key Tasks:**
- [ ] 创建集成测试脚本
- [ ] 创建 E2E 验证脚本
- [ ] 编写测试文档
- [ ] 收集反馈，优化体验

---
*Roadmap created: 2026-01-31*
*Last updated: 2026-01-31 after Phase 5 gap closure planning*
