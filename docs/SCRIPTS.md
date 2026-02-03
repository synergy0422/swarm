# AI Swarm 脚本索引

本文档列出所有运维脚本及其用法。脚本分为两类：**核心脚本**（日常运维必需）和**实用脚本**（辅助工具）。

**注意**：`swarm_e2e_test.sh` 仅用于集成验证/测试用途，不作为日常运维脚本，因此不包含在此文档中。

---

## 目录

- [配置脚本](#配置脚本)
- [通信脚本](#通信脚本)
- [任务管理脚本](#任务管理脚本)
- [系统工具脚本](#系统工具脚本)
- [实用脚本](#实用脚本)

---

## 布局脚本

### swarm_layout_5.sh

**用途：** 5 窗格 tmux 布局脚本，在单个窗口中创建 5 个窗格。

**布局结构：**
```
┌─────────────────┬────────────────────┐
│      master     │      worker-0      │
│                 ├────────────────────┤
│      codex      │      worker-1      │
│                 ├────────────────────┤
│                 │      worker-2      │
└─────────────────┴────────────────────┘
```

**参数：**

| 参数 | 说明 |
|------|------|
| `--session, -s NAME` | tmux 会话名称 |
| `--workdir, -d DIR` | 工作目录 |
| `--left-ratio, -l PCT` | 左侧垂直分割比例 (50-80) |
| `--codex-cmd, -c CMD` | codex 窗格执行的命令 |
| `--attach, -a` | 创建后附加到会话 |
| `--help, -h` | 显示帮助信息 |

**环境变量：**

| 变量 | 说明 |
|------|------|
| `CLAUDE_SESSION` | 会话名称覆盖 |
| `SWARM_WORKDIR` | 工作目录覆盖（默认当前目录） |
| `CODEX_CMD` | codex 命令覆盖（默认 "codex --yolo"） |

**示例：**

```bash
# 基本用法
./scripts/swarm_layout_5.sh

# 创建并附加
./scripts/swarm_layout_5.sh --attach

# 自定义会话名称
./scripts/swarm_layout_5.sh --session my-session

# 自定义工作目录
./scripts/swarm_layout_5.sh --workdir /path/to/project

# 自定义 codex 命令
./scripts/swarm_layout_5.sh --codex-cmd "codex --yolo --model o1"

# 调整左侧比例
./scripts/swarm_layout_5.sh --left-ratio 60

# 使用环境变量
SWARM_WORKDIR=/my/project ./scripts/swarm_layout_5.sh
CODEX_CMD="codex --yolo" ./scripts/swarm_layout_5.sh
```

**自定义布局比例：**

```bash
# 左侧 60% master，40% codex
./scripts/swarm_layout_5.sh --left-ratio 60

# 左侧 70% master，30% codex
./scripts/swarm_layout_5.sh --left-ratio 70
```

**自定义 codex 命令：**

```bash
# 使用特定模型
./scripts/swarm_layout_5.sh --codex-cmd "codex --yolo --model o1"

# 添加额外参数
./scripts/swarm_layout_5.sh --codex-cmd "codex --yolo --system 'You are an expert'"
```

**依赖：** `_config.sh`, `_common.sh`, tmux

---

### _config.sh

**用途：** 统一配置入口，提供所有脚本共享的配置值。

**参数：** 无（被 source，无执行参数）

**示例：**

```bash
# 在其他脚本中引入配置
source scripts/_config.sh

# 验证配置已加载
echo "SWARM_STATE_DIR=$SWARM_STATE_DIR"
echo "SESSION_NAME=$SESSION_NAME"
```

**更多用法：**

```bash
# 检查配置是否存在
test -n "$SWARM_STATE_DIR" && echo "配置已设置"

# 查看所有配置变量
env | grep SWARM
```

**依赖：** 无（被其他脚本 source）

---

### _common.sh

**用途：** 共享库函数，提供日志、配置读取等通用功能。

**参数：** 无（被 source，无执行参数）

**示例：**

```bash
# 在其他脚本中引入共享库
source scripts/_common.sh

# 使用日志函数
log_info "这是一条信息日志"
log_warn "这是一条警告日志"
log_error "这是一条错误日志"

# 使用配置变量
echo "状态目录: $SWARM_STATE_DIR"
echo "会话名称: $SESSION_NAME"
```

**更多用法：**

```bash
# 调试日志（需要设置 LOG_LEVEL=DEBUG）
LOG_LEVEL=DEBUG log_debug "详细调试信息"

# 使用结构化日志输出
echo "$SWARM_STATE_DIR/status.log" | jq '.'
```

**依赖：** `_config.sh`

---

## 通信脚本

### claude_comm.sh

**用途：** Claude CLI 通信命令，支持任务发送、状态轮询和窗口状态查询。

**参数：**

| 参数 | 说明 |
|------|------|
| `send <window> <task_id> "<description>"` | 发送任务到窗口（带 [TASK] 前缀） |
| `send-raw <window> "<message>"` | 发送原始消息（无前缀） |
| `poll <window> [timeout] [task_id]` | 轮询标记响应（默认超时 30 秒） |
| `status <window>` | 获取窗口状态 |

**示例：**

```bash
# 发送任务到 worker-0
./scripts/claude_comm.sh send worker-0 task-001 "创建文件 hello.py"

# 发送原始消息（协议设置）
./scripts/claude_comm.sh send-raw worker-0 "请开始处理任务"

# 轮询任务状态（默认 30 秒超时）
./scripts/claude_comm.sh poll worker-0 30 task-001

# 查询窗口当前状态
./scripts/claude_comm.sh status worker-0

# 指定会话名称
./scripts/claude_comm.sh --session custom-session send worker-0 task-001 "任务描述"
```

**高级用法：**

```bash
# 结合 claude_poll.sh 使用
./scripts/claude_comm.sh send worker-0 task-001 "任务描述" &
./scripts/claude_poll.sh

# 批量发送任务到不同 Worker
for i in 0 1 2; do
    ./scripts/claude_comm.sh send "worker-$i" "task-00$i" "任务 $i"
done

# 使用环境变量指定会话
CLAUDE_SESSION=swarm-test ./scripts/claude_comm.sh send worker-0 task-001 "测试任务"

# 等待所有 Worker 完成
./scripts/claude_poll.sh | grep -q "3/3.*DONE" && echo "所有任务完成"
```

**依赖：** `_common.sh`, tmux

---

### claude_poll.sh

**用途：** 持续监控 Worker 窗口，自动检测 [DONE] 和 [ERROR] 标记。

**参数：** 无（持续运行，按 Ctrl+C 停止）

**选项：**

| 选项 | 说明 |
|------|------|
| `--session <name>` | 指定 tmux 会话名称（默认：swarm-claude-default） |

**示例：**

```bash
# 开始监控所有 Worker
./scripts/claude_poll.sh

# 指定会话监控
./scripts/claude_poll.sh --session custom-session
```

**高级用法：**

```bash
# 在后台运行监控
./scripts/claude_poll.sh > poll.log 2>&1 &

# 监控特定窗口（需要修改脚本）
# claude_poll.sh 默认监控 worker-0, worker-1, worker-2

# 实时过滤输出
./scripts/claude_poll.sh | grep -E "(DONE|ERROR)"
```

**依赖：** `_common.sh`, tmux

---

### claude_status.sh

**用途：** 快速状态检查，一次性显示所有 4 个窗口的最后 10 行输出。

**参数：** 无（显示所有窗口状态）

**选项：**

| 选项 | 说明 |
|------|------|
| `--session <name>` | 指定 tmux 会话名称（默认：swarm-claude-default） |

**示例：**

```bash
# 快速状态检查
./scripts/claude_status.sh

# 指定会话
./scripts/claude_status.sh --session swarm-claude-default

# 环境变量方式指定会话
CLAUDE_SESSION=custom-session ./scripts/claude_status.sh
```

**依赖：** `_common.sh`, tmux

---

### claude_auto_rescue.sh

**用途：** 自动检测并确认 Claude CLI 的确认提示（如 [y/n]、回车继续等）。

**参数：**

| 参数 | 说明 |
|------|------|
| `check <window>` | 检查并自动确认一次 |
| `run <window>` | 持续监控并自动确认 |
| `status` | 显示各窗口最后操作时间 |

**选项：**

| 选项 | 说明 |
|------|------|
| `--session <name>` | 指定 tmux 会话名称 |

**示例：**

```bash
# 检查 worker-0 是否有待确认提示
./scripts/claude_auto_rescue.sh check worker-0

# 持续监控 worker-0（按 Ctrl+C 停止）
./scripts/claude_auto_rescue.sh run worker-0

# 查看自动确认状态
./scripts/claude_auto_rescue.sh status

# 指定会话
./scripts/claude_auto_rescue.sh --session custom-session check worker-0
```

**高级用法：**

```bash
# 同时监控所有 Worker（需要循环调用）
for w in worker-0 worker-1 worker-2; do
    ./scripts/claude_auto_rescue.sh check "$w"
done

# 使用 tmux new-window 启动监控
tmux new-window -n auto-rescue "./scripts/claude_auto_rescue.sh run worker-0"

# 在后台运行自动确认
nohup ./scripts/claude_auto_rescue.sh run worker-0 > rescue.log 2>&1 &
```

**依赖：** `_common.sh`, tmux

---

## 任务管理脚本

### swarm_task_wrap.sh

**用途：** 任务生命周期包装器，提供完整的任务执行流程（锁获取、状态广播、执行、状态更新、锁释放）。

**参数：**

| 参数 | 说明 |
|------|------|
| `run <task_id> <worker> <command> [args...]` | 完整任务生命周期 |
| `acquire-only <task_id> [worker]` | 仅获取锁并写入 START 状态 |
| `release-only <task_id> [worker]` | 仅释放锁并写入 DONE 状态 |
| `skip <task_id> [worker] <reason>` | 写入 SKIP 状态（不操作锁） |
| `wait <task_id> [worker] <reason>` | 写入 WAIT 状态（不操作锁） |

**选项：**

| 选项 | 说明 |
|------|------|
| `--ttl SECONDS` | 锁 TTL（秒），默认不过期 |
| `--no-status` | 跳过状态日志记录 |

**示例：**

```bash
# 完整任务生命周期
./scripts/swarm_task_wrap.sh run task-001 worker-0 echo hello

# 带 TTL 的任务（1 小时过期）
./scripts/swarm_task_wrap.sh run --ttl 3600 task-002 worker-1 python process.py

# 仅获取锁
./scripts/swarm_task_wrap.sh acquire-only task-003 worker-0

# 仅释放锁
./scripts/swarm_task_wrap.sh release-only task-003 worker-0

# 跳过任务
./scripts/swarm_task_wrap.sh skip task-004 "依赖未就绪"

# 等待任务
./scripts/swarm_task_wrap.sh wait task-005 "等待上游依赖"

# 测试模式（不记录状态）
./scripts/swarm_task_wrap.sh --no-status run task-006 worker-2 ./test.sh
```

**依赖：** `_common.sh`, `swarm_lock.sh`, `swarm_status_log.sh`

---

### swarm_lock.sh

**用途：** 任务锁操作，支持原子的获取/释放/检查/列表操作。

**参数：**

| 参数 | 说明 |
|------|------|
| `acquire <task_id> <worker> [ttl_seconds]` | 原子获取任务锁 |
| `release <task_id> <worker>` | 释放锁（严格验证持有者） |
| `check <task_id>` | 检查锁状态（活跃/过期） |
| `list` | 列出所有活跃锁 |

**示例：**

```bash
# 获取锁（不过期）
./scripts/swarm_lock.sh acquire task-001 worker-0

# 获取锁（1 小时过期）
./scripts/swarm_lock.sh acquire task-001 worker-0 3600

# 释放锁
./scripts/swarm_lock.sh release task-001 worker-0

# 检查单个锁状态
./scripts/swarm_lock.sh check task-001

# 列出所有锁
./scripts/swarm_lock.sh list
```

**依赖：** `_common.sh`, Python 3

---

### swarm_broadcast.sh

**用途：** 状态广播，在 Worker 窗口内广播状态更新。

**参数：**

| 参数 | 说明 |
|------|------|
| `start <task_id> [reason]` | 广播 START 状态 |
| `done <task_id> [reason]` | 广播 DONE 状态 |
| `error <task_id> [reason]` | 广播 ERROR 状态 |
| `wait <task_id> [reason]` | 广播 WAIT 状态 |

**选项：**

| 选项 | 说明 |
|------|------|
| `--session <name>` | 指定 tmux 会话名称 |

**示例：**

```bash
# 广播任务开始
./scripts/swarm_broadcast.sh start task-001

# 广播任务完成（带原因）
./scripts/swarm_broadcast.sh done task-001 "处理完成"

# 广播任务错误
./scripts/swarm_broadcast.sh error task-002 "文件不存在"

# 广播等待状态
./scripts/swarm_broadcast.sh wait task-003 "等待依赖"

# 指定会话
./scripts/swarm_broadcast.sh --session custom-session start task-004
```

**高级用法：**

```bash
# 在脚本中调用广播
source scripts/_common.sh
./scripts/swarm_broadcast.sh start task-005
./scripts/swarm_broadcast.sh done task-005 "脚本执行完成"

# 批量广播多个任务
for i in task-006 task-007 task-008; do
    ./scripts/swarm_broadcast.sh start "$i"
done

# 结合 swarm_task_wrap.sh 使用
./scripts/swarm_task_wrap.sh run task-009 worker-0 ./script.sh
```

**依赖：** `_common.sh`, `swarm_status_log.sh`, tmux

---

## 系统工具脚本

### swarm_selfcheck.sh

**用途：** 一键系统健康检查，验证 tmux、脚本、配置和状态目录。

**参数：** 无

**选项：**

| 选项 | 说明 |
|------|------|
| `-v, --verbose` | 显示详细检查输出 |
| `-q, --quiet` | 仅报告失败项 |
| `-h, --help` | 显示帮助信息 |

**示例：**

```bash
# 常规检查
./scripts/swarm_selfcheck.sh

# 详细输出
./scripts/swarm_selfcheck.sh -v

# 仅显示失败项
./scripts/swarm_selfcheck.sh -q
```

**高级用法：**

```bash
# 在 CI/CD 中使用
if ./scripts/swarm_selfcheck.sh -q; then
    echo "环境检查通过"
    exit 0
else
    echo "环境检查失败"
    exit 1
fi

# 检查特定组件（需要脚本支持或手动检查）
# tmux 检查
tmux -V

# 脚本权限检查
ls -la scripts/*.sh | awk '{if($1!~/-x/) print}'

# 配置检查
source scripts/_config.sh && test -d "$SWARM_STATE_DIR"
```

**依赖：** `_config.sh`, `_common.sh`

---

## 诊断快照脚本

### swarm_snapshot.sh

**用途：** 一键采集 tmux swarm 运行状态用于诊断分析。脚本为只读操作，不会修改 SWARM_STATE_DIR 中任何文件。

**参数：**

| 参数 | 说明 |
|------|------|
| `-s, --session NAME` | tmux 会话名称（默认：swarm-claude-default） |
| `-n, --lines N` | 每个窗格捕获的行数（默认：50） |
| `-o, --out DIR` | 输出目录（默认：/tmp/ai_swarm_snapshot_<timestamp>） |
| `-h, --help` | 显示帮助信息 |

**环境变量：**

| 变量 | 说明 |
|------|------|
| `CLAUDE_SESSION` | 会话名称覆盖 |
| `SNAPSHOT_LINES` | 捕获行数覆盖 |
| `SNAPSHOT_DIR` | 输出目录覆盖 |

**示例：**

```bash
# 基本用法（采集默认会话）
./scripts/swarm_snapshot.sh

# 指定会话名称
./scripts/swarm_snapshot.sh --session my-session

# 自定义输出行数
./scripts/swarm_snapshot.sh --lines 100

# 自定义输出目录
./scripts/swarm_snapshot.sh --out /path/to/snapshot

# 环境变量方式
CLAUDE_SESSION=test-session SNAPSHOT_LINES=200 ./scripts/swarm_snapshot.sh
```

**高级用法：**

```bash
# 采集并立即查看摘要
./scripts/swarm_snapshot.sh && cat /tmp/ai_swarm_snapshot_*/meta/summary.txt

# 批量采集多个会话
for session in swarm-default test-session; do
    ./scripts/swarm_snapshot.sh --session "$session" --out "/snapshots/$session"
done

# 错误处理（在脚本中使用）
if ./scripts/swarm_snapshot.sh --session "$SESSION" --out "/tmp/$SESSION"; then
    echo "Snapshot created successfully"
else
    echo "Snapshot completed with errors"
fi
```

**输出结构：**

```
<snapshot_dir>/
  tmux/
    structure.txt   # 会话、窗口、窗格结构
  panes/
    <session>.<window>.<pane>.txt  # 各窗格输出（带前缀）
  state/
    status.log      # 只读复制（如果存在）
  locks/
    list.txt        # 只读列出（如果存在）
  meta/
    git.txt         # git 状态、分支、提交
    summary.txt     # 快照概览和错误摘要
```

**只读约束：** 脚本不会对 `$SWARM_STATE_DIR` 执行任何写操作（mkdir, cp, rm 等）。状态文件通过只读复制方式采集。

**依赖：** `_common.sh`, tmux

---

## 实用脚本

### swarm_status_log.sh

**用途：** 状态日志记录工具，独立运行，与 claude_status.sh 功能互补。用于记录、查询和追踪任务状态。

**参数：**

| 参数 | 说明 |
|------|------|
| `append <type> <worker> <task_id> [reason]` | 添加状态记录 |
| `tail <n>` | 显示最后 N 条记录（默认 10） |
| `query <task_id>` | 查询特定任务的状态记录 |

**有效类型：** `START`, `DONE`, `ERROR`, `WAIT`, `HELP`, `SKIP`

**示例：**

```bash
# 添加 START 记录
./scripts/swarm_status_log.sh append START worker-0 task-001

# 添加 DONE 记录（带原因）
./scripts/swarm_status_log.sh append DONE worker-0 task-001 "处理完成"

# 添加 ERROR 记录（带原因）
./scripts/swarm_status_log.sh append ERROR worker-1 task-002 "文件不存在"

# 查看最后 10 条记录
./scripts/swarm_status_log.sh tail

# 查看最后 20 条记录
./scripts/swarm_status_log.sh tail 20

# 查询特定任务
./scripts/swarm_status_log.sh query task-001

# 自定义状态目录
SWARM_STATE_DIR=/custom/path ./scripts/swarm_status_log.sh append START worker-0 task-003
```

**更多用法：**

```bash
# 导出状态到 JSON
cat /tmp/ai_swarm/status.log | jq '.' > status.json

# 统计任务完成情况
cat /tmp/ai_swarm/status.log | jq -r '.type' | sort | uniq -c

# 查找特定 Worker 的所有任务
jq '.[] | select(.worker == "worker-0")' /tmp/ai_swarm/status.log

# 统计错误数量
grep '"ERROR"' /tmp/ai_swarm/status.log | wc -l
```

**依赖：** `_common.sh`

---

## 脚本依赖关系图

```
_layout_5.sh
    |
    +-- _config.sh
    +-- _common.sh
        |
        +-- _config.sh
```
或
```
_common.sh
    |
    +-- _config.sh
        |
        +-- claude_comm.sh (tmux)
        +-- claude_poll.sh (tmux)
        +-- claude_status.sh (tmux)
        +-- claude_auto_rescue.sh (tmux)
        +-- swarm_broadcast.sh (swarm_status_log.sh, tmux)
        +-- swarm_task_wrap.sh (swarm_lock.sh, swarm_status_log.sh)
        +-- swarm_selfcheck.sh (_config.sh)
        +-- swarm_snapshot.sh (tmux)
        |
_config.sh
```

---

## 快速参考

### 日常运维命令

```bash
# 检查状态
./scripts/claude_status.sh

# 监控进度
./scripts/claude_poll.sh

# 系统健康检查
./scripts/swarm_selfcheck.sh
```

### 任务管理命令

```bash
# 发送任务
./scripts/claude_comm.sh send worker-0 task-001 "任务描述"

# 轮询状态
./scripts/claude_comm.sh poll worker-0 30 task-001

# 任务包装执行
./scripts/swarm_task_wrap.sh run task-001 worker-0 ./command.sh
```

### 故障恢复命令

```bash
# 检查锁
./scripts/swarm_lock.sh list

# 查看日志
./scripts/swarm_status_log.sh tail 20

# 清理锁
rm -f /tmp/ai_swarm/locks/*
```
