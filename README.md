# AI Swarm - Multi-Agent Task Processing System

A distributed multi-agent system where a Master coordinates multiple Worker nodes to process tasks in parallel using Anthropic's Claude API.

## Features

- **Parallel Task Processing**: Multiple workers process tasks concurrently
- **Tmux Integration**: Visual session management with real-time output
- **Fault Tolerance**: Automatic worker rescuing and wait state detection
- **Task Locking**: Prevents duplicate task execution across workers
- **Cost Tracking**: Built-in token usage and cost calculation

## Usage

```bash
# Initialize swarm environment
swarm init

# Launch cluster (master + 3 workers)
swarm up

# Attach to tmux session
tmux attach -t swarm-default

# Check status
swarm status

# Stop cluster
swarm down
```

## Requirements

- Python 3.8+
- tmux
- libtmux (`pip install libtmux`)
- ANTHROPIC_API_KEY or LLM_BASE_URL environment variable

## Installation

```bash
# Install from source
pip install -e .

# Or install dependencies manually
pip install requests libtmux
```

## Configuration

Set environment variables **before** running swarm commands:

```bash
# Option 1: Direct Anthropic API
export ANTHROPIC_API_KEY="sk-ant-..."

# Option 2: Local proxy (cc-switch or similar)
export LLM_BASE_URL="http://127.0.0.1:15721"
export ANTHROPIC_API_KEY="dummy"  # Optional placeholder

# Optional: Custom swarm directory
export AI_SWARM_DIR="/path/to/swarm/dir"

# Optional: Poll interval for master (default: 1.0)
export AI_SWARM_POLL_INTERVAL="1.0"
```

**Note:** LLM_BASE_URL is inherited by tmux worker windows. Make sure to export it in the same shell before running `swarm up`.
For cc-switch, set `LLM_BASE_URL="http://127.0.0.1:15721/v1/messages"` and optionally `ANTHROPIC_API_KEY="dummy"` before launching.
You can also run `swarm init` to see the default cc-switch environment example if LLM_BASE_URL is not set.

## Commands

### `swarm init`
Initialize swarm environment, check dependencies, and create directory structure.

### `swarm up [--workers N] [--cluster-id ID]`
Launch tmux session with master + N workers (default: 3 workers).

### `swarm master [--cluster-id ID]`
Launch only the master process (for debugging).

### `swarm worker --id N [--cluster-id ID]`
Launch a single worker with specified ID (for debugging).

### `swarm status [--cluster-id ID]`
Display tmux session and agent status.

### `swarm down [--cluster-id ID]`
Terminate swarm tmux session.

### `swarm task add "<prompt>"`
Add task via FIFO input channel (requires `AI_SWARM_INTERACTIVE=1`).

```bash
# Add task from argument
swarm task add "Review PR #123"

# Add task from stdin
echo "Fix bug" | swarm task add -
```

## 自然语言发布任务

当 master 在 tmux 后台运行时，可以通过 FIFO 输入通道发布任务：

```bash
# 启用交互模式
export AI_SWARM_INTERACTIVE=1

# 启动 master
python3 -m swarm.cli master --cluster-id default
```

### 发布任务

**方式 1: CLI 命令**
```bash
swarm task add "Review PR #123"
echo "Fix bug" | swarm task add -
```

**方式 2: Bash 脚本**
```bash
./scripts/swarm_fifo_write.sh write "Review PR #123"
echo "Task" | ./scripts/swarm_fifo_write.sh write -
```

**方式 3: 直接写入 FIFO**
```bash
echo "Task description" > $AI_SWARM_DIR/master_inbox
```

### FIFO 指令

- `/task <prompt>` - 创建任务
- `/help` - 显示帮助
- `/quit` - 停止输入线程（master 继续运行）
- 无前缀文本 - 直接作为任务

**注意:** 需要 master 运行并设置 `AI_SWARM_INTERACTIVE=1`

## 主脑窗口任务发布

从 Claude Code 主脑窗口（codex 窗口）直接发布任务到 swarm（自动监控 + 派发）。

### 重要说明

**Bridge 监控的是 codex 窗口的输出，不是 master 进程窗口。**

必须在 **codex 窗口**（运行 Claude Code 的窗口）输入 `/task` 或 `TASK:` 开头的行，Bridge 才能捕获到。

```
codex 窗口                    Bridge 进程
    │                            │
    │  输入: /task ...           │
    │  ────────────────────────────────▶
    │  回显到 pane              │
    │  ────────────────────────────────▶ capture-pane
    │                              parse → dedupe → FIFO
    │                                   │
    ▼                                   ▼
```

### 使用方式

```bash
# 1. 启动 tmux session（使用 2 窗口布局脚本）
./scripts/swarm_layout_5.sh --no-attach

# 2. 查看输出获取 codex pane ID
# 脚本会输出类似：export AI_SWARM_BRIDGE_PANE=%3

# 3. 设置环境变量（根据脚本输出）
export AI_SWARM_BRIDGE_PANE=<pane_id>

# 4. 新终端启动 bridge
AI_SWARM_INTERACTIVE=1 ./scripts/swarm_bridge.sh start

# 5. 在 codex 窗口输入（以下内容必须回显到 pane）：
/task Review PR #123 and leave comments
TASK: Fix authentication bug in login module
```

**重要：** Bridge 指向的是 codex 窗口（你输入 /task 的地方），不是 master 进程窗口！

### 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `AI_SWARM_BRIDGE_SESSION` | tmux session 名称 | `swarm-claude-default` |
| `AI_SWARM_BRIDGE_WINDOW` | tmux window 名称（codex 窗口） | `codex-master` |
| `AI_SWARM_BRIDGE_PANE` | tmux pane_id（最高优先级，推荐使用） | - |
| `AI_SWARM_BRIDGE_LINES` | capture-pane 行数 | `200` |
| `AI_SWARM_BRIDGE_POLL_INTERVAL` | 轮询间隔（秒） | `1.0` |
| `AI_SWARM_INTERACTIVE` | 启用交互模式（必须为 `1`） | `0` |

### 命令

```bash
./scripts/swarm_bridge.sh start    # 启动 bridge
./scripts/swarm_bridge.sh stop     # 停止 bridge
./scripts/swarm_bridge.sh status   # 检查状态
```

### 日志查看

```bash
# Bridge 调试日志
tail -f $AI_SWARM_DIR/bridge.log

# 状态日志（JSONL）
tail -f $AI_SWARM_DIR/status.log

# 任务是否被派发
grep "BRIDGE" $AI_SWARM_DIR/status.log
```

### 故障排查

- **tmux session 不存在**: 先创建 tmux session 或设置 `AI_SWARM_BRIDGE_SESSION`
- **FIFO 无 reader**: 确认 master 已启动（`AI_SWARM_INTERACTIVE=1`）
- **任务未发送**: 检查 `bridge.log` 和 `status.log`
- **Claude 不回显**: 确认 Claude Code 配置为回显命令到终端

## Architecture

```
┌─────────────────────────────────────┐
│         Tmux Session                │
│  ┌──────────┬──────────┬──────────┐ │
│  │  Master  │ Worker-1 │ Worker-2 │ │
│  │          │          │          │ │
│  │  - Scan  │  - Poll  │  - Poll  │ │
│  │  - Assign│  - Task  │  - Task  │ │
│  │  - Rescue│  - API   │  - API   │ │
│  └──────────┴──────────┴──────────┘ │
│         ↓        ↓         ↓        │
│  ┌──────────────────────────────┐  │
│  │     Shared Filesystem       │  │
│  │  - status.log (JSON Lines)  │  │
│  │  - tasks.json                │  │
│  │  - locks/*.lock              │  │
│  │  - results/*.md              │  │
│  └──────────────────────────────┘  │
└─────────────────────────────────────┘
```

## 2 窗口布局 (V1.92)

V1.92 引入了新的 2 窗口布局，将窗格分离到两个独立窗口：

**窗口 1 (codex-master):**
```
┌─────────────────────┬────────────────────────────┐
│                     │                            │
│        codex        │          master            │
│                     │                            │
└─────────────────────┴────────────────────────────┘
```

**窗口 2 (workers):**
```
┌───────────────┬───────────────┬───────────────┐
│               │               │               │
│    worker-0   │    worker-1   │    worker-2   │
│               │               │               │
└───────────────┴───────────────┴───────────────┘
```

**注意：** 此布局需要配置 Bridge 才能监控 codex 窗口。

### Bridge 配置

运行布局脚本后，需要设置 `AI_SWARM_BRIDGE_PANE` 环境变量：

```bash
# 运行布局脚本后，查看输出：
./scripts/swarm_layout_5.sh
# 输出类似：export AI_SWARM_BRIDGE_PANE=%3

# 设置环境变量
export AI_SWARM_BRIDGE_PANE=<pane_id>

# 启动 Bridge
AI_SWARM_INTERACTIVE=1 ./scripts/swarm_bridge.sh start
```

### 使用方法

```bash
# 基本用法（默认工作目录为当前目录）
./scripts/swarm_layout_5.sh

# 创建并附加
./scripts/swarm_layout_5.sh --attach

# 自定义会话名称
./scripts/swarm_layout_5.sh --session my-session

# 自定义工作目录
./scripts/swarm_layout_5.sh --workdir /path/to/project

# 自定义 codex 命令
./scripts/swarm_layout_5.sh --codex-cmd "codex --yolo --model o1"
```

### 参数说明

| 参数 | 说明 |
|------|------|
| `--session, -s` | tmux 会话名称 |
| `--workdir, -d` | 工作目录 |
| `--codex-cmd, -c` | codex 窗格执行的命令 |
| `--attach, -a` | 创建后附加到会话 |

### 快速启动

在任意目录执行以下命令，即可使用本地代理启动 2 窗口布局：

```bash
LLM_BASE_URL="http://127.0.0.1:15721" SWARM_WORKDIR="$PWD" CODEX_CMD="codex --yolo" ./scripts/swarm_layout_5.sh --attach
```

### 环境变量

| 变量 | 说明 |
|------|------|
| `CLAUDE_SESSION` | 会话名称覆盖 |
| `SWARM_WORKDIR` | 工作目录覆盖 |
| `CODEX_CMD` | codex 命令覆盖 |

附加命令：

```bash
tmux attach -t <session-name>
```

## 诊断快照

v1.8 引入了诊断快照功能，用于采集 tmux swarm 运行状态进行诊断分析。

### 使用方法

```bash
# 基本用法（采集默认会话）
./scripts/swarm_snapshot.sh

# 指定会话名称
./scripts/swarm_snapshot.sh --session my-session

# 自定义输出行数（默认 50）
./scripts/swarm_snapshot.sh --lines 100

# 自定义输出目录
./scripts/swarm_snapshot.sh --out /path/to/snapshot
```

### 参数说明

| 参数 | 说明 |
|------|------|
| `--session, -s` | tmux 会话名称 |
| `--lines, -n` | 每个窗格捕获的行数（默认 50） |
| `--out, -o` | 输出目录（默认 /tmp/ai_swarm_snapshot_<timestamp>） |
| `--help, -h` | 显示帮助信息 |

### 输出内容

快照会创建以下目录结构：
```
<snapshot_dir>/
  tmux/           # tmux 结构信息
    structure.txt # 会话、窗口、窗格结构
  panes/          # 各窗格输出（带 session:window.pane 前缀）
    <session>.<window>.<pane>.txt
  state/          # 状态文件（只读复制）
    status.log     #（如果存在于 SWARM_STATE_DIR）
  locks/          # 锁目录列表（只读）
    list.txt       #（如果 locks/ 存在于 SWARM_STATE_DIR）
  meta/           # git 信息和摘要
    git.txt        # git 状态、分支、提交记录
    summary.txt    # 快照概览和错误摘要
```

**注意：** 快照脚本为只读操作，不会修改 SWARM_STATE_DIR 中任何文件。

## Claude Tasks 协作流程

v1.85 引入了 CLAUDE_CODE_TASK_LIST_ID 桥接功能，支持与外部任务系统（如 Claude Code 的 Tasks）集成，实现自动化的 claim -> lock -> work -> done/fail 闭环。

### 架构概览

```
┌─────────────────────────┐    ┌─────────────────────────┐
│   Claude Code Tasks     │    │   AI Swarm Worker        │
│                         │    │                         │
│  - Create task list     │───>│  - Claim task via bridge │
│  - Assign CLAUDE_CODE_  │    │  - Acquire lock          │
│    TASK_LIST_ID         │    │  - Execute work          │
│  - Monitor progress     │<───│  - Report done/fail      │
│                         │    │  - Release lock          │
└─────────────────────────┘    └─────────────────────────┘
            │                            │
            │                            v
            │                   ┌─────────────────────────┐
            │                   │   swarm_tasks_bridge   │
            │                   │                        │
            └──────────────────>│  - claim: lock+start  │
                                │  - done: unlock+done   │
                                │  - fail: unlock+error  │
                                └─────────────────────────┘
```

### 命令参考

| 命令 | 参数 | 说明 |
|------|------|------|
| `claim <task_id> <worker> [lock_key]` | 获取任务锁并记录 START 状态 |
| `done <task_id> <worker> [lock_key]` | 释放任务锁并记录 DONE 状态 |
| `fail <task_id> <worker> <reason> [lock_key]` | 释放任务锁并记录 ERROR 状态 |

### 退出码

| 命令 | 退出码 | 含义 |
|------|--------|------|
| claim | 0 | 成功获取锁 |
| claim | 2 | 锁已被占用 |
| claim | 1 | 其他错误 |
| done | 0 | 成功释放锁 |
| done | 1 | 释放失败 |
| fail | 0 | 成功记录错误 |
| fail | 1 | 记录失败 |

### 完整工作流示例

```bash
# 1. Worker claim 任务（获取锁 + 记录 START）
./scripts/swarm_tasks_bridge.sh claim task-001 worker-0

# 2. 执行实际工作...
echo "Processing task-001..."

# 3. 任务完成（释放锁 + 记录 DONE）
./scripts/swarm_tasks_bridge.sh done task-001 worker-0
```

### 错误处理示例

```bash
# 任务失败场景
./scripts/swarm_tasks_bridge.sh fail task-002 worker-1 "Validation failed: missing required field"
```

### 自定义锁键

```bash
# 使用自定义 lock_key（适用于多任务共享同一个锁）
./scripts/swarm_tasks_bridge.sh claim task-003 worker-0 feature-x-lock
./scripts/swarm_tasks_bridge.sh done task-003 worker-0 feature-x-lock
```

### 与外部任务系统集成

在外部任务系统的 Worker 脚本中集成：

```bash
#!/usr/bin/env bash
source "$(dirname "$0")/swarm_tasks_bridge.sh"

# 获取任务 ID（来自外部系统）
TASK_ID="$CLAUDE_CODE_TASK_LIST_ID"
WORKER="worker-$WORKER_ID"

# Claim 任务
"$SCRIPT_DIR/swarm_tasks_bridge.sh" claim "$TASK_ID" "$WORKER" || {
    echo "Task already claimed or lock held by another worker"
    exit 1
}

# 执行实际工作
process_task "$TASK_ID"

# 根据结果报告状态
if [ $? -eq 0 ]; then
    "$SCRIPT_DIR/swarm_tasks_bridge.sh" done "$TASK_ID" "$WORKER"
else
    "$SCRIPT_DIR/swarm_tasks_bridge.sh" fail "$TASK_ID" "$WORKER" "Processing failed"
fi
```

## Development

```bash
# Run tests
pytest

# Check test coverage
pytest --cov=swarm --cov-report=html

# Lint
flake8 swarm/
```

### E2E (cc-switch)

```bash
export LLM_BASE_URL="http://127.0.0.1:15721/v1/messages"
export ANTHROPIC_API_KEY="dummy"
python3 scripts/swarm_e2e_ccswitch_test.py
```

## Maintenance Guide

Complete maintenance documentation available at [docs/MAINTENANCE.md](docs/MAINTENANCE.md):

- Environment recovery procedures
- Troubleshooting guide
- Emergency procedures (5-step recovery)
- Maintenance checklist

## Script Index

All script documentation available at [docs/SCRIPTS.md](docs/SCRIPTS.md):

- Configuration scripts (_config.sh, _common.sh)
- Communication scripts (claude_comm.sh, claude_poll.sh, claude_status.sh, claude_auto_rescue.sh)
- Task management scripts (swarm_task_wrap.sh, swarm_lock.sh, swarm_broadcast.sh)
- System tools (swarm_selfcheck.sh, swarm_snapshot.sh)
- Utility scripts (swarm_status_log.sh)

## Command Mapping

Note: `claude status` is a Claude CLI command, not a swarm command. Swarm commands use `swarm <verb>` format.

| Command | Script File | Description |
|---------|-------------|-------------|
| `claude status` | `claude_status.sh` | Quick status check for all windows |
| `swarm task-wrap` | `swarm_task_wrap.sh` | Task lifecycle wrapper |
| `swarm selfcheck` | `swarm_selfcheck.sh` | System health check |
| `swarm snapshot` | `swarm_snapshot.sh` | Diagnostic snapshot collection |
| `swarm lock` | `swarm_lock.sh` | Task lock operations |
| `swarm broadcast` | `swarm_broadcast.sh` | Status broadcasting |
| `swarm rescue` | `claude_auto_rescue.sh` | Auto-confirm prompts |
| `swarm tasks-bridge` | `swarm_tasks_bridge.sh` | CLAUDE_CODE_TASK_LIST_ID bridge for lock/state operations |
| `swarm bridge` | `swarm_bridge.sh` | Claude master window bridge for task dispatch |
| `swarm fifo-write` | `swarm_fifo_write.sh` | Write to FIFO input channel |

## Changelog

Version history available at [CHANGELOG.md](CHANGELOG.md).

## License

MIT License - See LICENSE file for details.
