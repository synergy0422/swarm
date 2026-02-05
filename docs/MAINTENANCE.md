# AI Swarm 维护指南

本指南提供系统维护、故障排查和紧急恢复的完整流程。适用于新维护者，无需历史上下文即可操作。

## 目录

- [维护入口](#维护入口)
- [环境恢复](#环境恢复)
- [故障排查](#故障排查)
- [紧急流程](#紧急流程)
- [维护清单](#维护清单)
- [最佳实践](#最佳实践)

---

## 维护入口

### 快速检查

运行系统自检脚本验证环境健康：

```bash
# 常规检查
./scripts/swarm_selfcheck.sh

# 详细输出
./scripts/swarm_selfcheck.sh -v

# 仅显示失败项
./scripts/swarm_selfcheck.sh -q
```

### 查看状态

使用 `claude status` 命令快速检查所有窗口状态：

```bash
# 快速状态检查（使用 claude_status.sh 脚本）
./scripts/claude_status.sh

# 指定会话名称
./scripts/claude_status.sh --session swarm-claude-default
```

此命令显示所有 4 个窗口（master, worker-0, worker-1, worker-2）的最后 10 行输出。

### 端到端验证（cc-switch）

使用 cc-switch 本地代理完成一次完整端到端测试：

```bash
export LLM_BASE_URL="http://127.0.0.1:15721/v1/messages"
export ANTHROPIC_API_KEY="dummy"
python3 scripts/swarm_e2e_ccswitch_test.py --timeout 120
```

输出说明：
1) 结果文件与任务状态完整链路验证（START → ASSIGNED → WAIT → DONE）
2) status.log / tasks.json / mailbox / results 证据可追踪
3) 失败时脚本返回非 0 并输出诊断信息

报告归档建议：将 `/tmp/swarm_e2e_report.jsonl` 复制到 `docs/reports/` 便于审计留痕。

### 持续监控

持续监控 Worker 窗口状态变化：

```bash
./scripts/claude_poll.sh

# 指定会话
./scripts/claude_poll.sh --session custom-session
```

---

## 环境恢复

### tmux 会话清理

清理残留的 tmux 会话：

```bash
# 查看所有会话
tmux ls

# 关闭指定会话
tmux kill-session -t swarm-claude-default

# 关闭所有 swarm 相关会话
tmux ls | grep '^swarm-' | cut -d: -f1 | xargs -I{} tmux kill-session -t {}
```

### 状态目录清理

清理 `/tmp/ai_swarm` 状态目录：

```bash
# 查看状态目录内容
ls -la /tmp/ai_swarm/

# 查看锁文件
ls -la /tmp/ai_swarm/locks/

# 清空状态目录（谨慎！）
rm -rf /tmp/ai_swarm/*
```

### 锁文件清理

单独清理锁文件：

```bash
# 查看所有锁
./scripts/swarm_lock.sh list

# 清理所有锁
rm -f /tmp/ai_swarm/locks/*

# 验证清理结果
./scripts/swarm_lock.sh list
```

### 重建完整环境

一键重建完整运行环境：

```bash
# 1. 备份现有状态
cp -r /tmp/ai_swarm /tmp/ai_swarm.backup.$(date +%Y%m%d%H%M%S)

# 2. 关闭所有会话
tmux ls | grep '^swarm-' | cut -d: -f1 | xargs -I{} tmux kill-session -t {} 2>/dev/null || true

# 3. 清理状态目录
rm -rf /tmp/ai_swarm/*
mkdir -p /tmp/ai_swarm/locks

# 4. 运行自检验证
./scripts/swarm_selfcheck.sh

# 5. 启动新会话
./run_claude_swarm.sh
```

---

## 故障排查

### 常见问题

| 问题 | 可能原因 | 解决方案 |
|------|----------|----------|
| Worker 窗口意外关闭 | LLM_BASE_URL 未配置 | 配置环境变量后重新启动 |
| 任务重复执行 | 锁文件未正确释放 | 清理锁文件后重试 |
| 状态不更新 | status.log 权限问题 | 检查并修复文件权限 |
| tmux 连接失败 | 会话不存在或已关闭 | 检查 `tmux ls` 确认会话状态 |
| API 调用失败 | ANTHROPIC_API_KEY 未设置 | 导出 API Key |

### 诊断命令

```bash
# 检查 tmux 会话状态
tmux ls

# 检查特定窗口内容
tmux capture-pane -t swarm-claude-default:worker-0 -p | tail -20

# 检查状态目录
ls -la /tmp/ai_swarm/

# 检查锁文件
./scripts/swarm_lock.sh list

# 检查最近状态日志
tail -20 /tmp/ai_swarm/status.log

# 检查脚本可执行权限
ls -la scripts/*.sh
```

### 错误日志查看

```bash
# 查看状态日志
./scripts/swarm_status_log.sh tail 20

# 查询特定任务状态
./scripts/swarm_status_log.sh query task-001

# 查看所有窗口实时状态
./scripts/claude_status.sh
```

---

## 紧急流程

当系统出现严重故障（如进程卡死、锁文件损坏、会话异常）时，按以下 **五步紧急恢复流程** 操作：

### 1. 备份 (Backup)

复制当前状态目录，以便事后分析：

```bash
cp -r /tmp/ai_swarm /tmp/ai_swarm.backup.$(date +%Y%m%d%H%M%S)
```

### 2. 优雅停 (Graceful Stop)

向所有 Worker 进程发送 SIGTERM 信号，等待它们正常退出：

```bash
pkill -TERM -f "claude.*worker"
echo "已发送 SIGTERM，等待 10 秒..."
sleep 10
```

### 3. 强杀 (Force Kill)

如果进程未停止，发送 SIGKILL 强制终止：

```bash
# 检查是否还有运行中的进程
ps aux | grep -E "claude.*worker" | grep -v grep

# 如果还有进程，强制终止
pkill -9 -f "claude.*worker"
```

### 4. 清锁 (Clear Locks)

移除所有锁文件，释放被占用的任务：

```bash
rm -f /tmp/ai_swarm/locks/*
echo "锁文件已清理"
```

### 5. 复验 (Verify)

确认系统处于安全状态，可以重新启动：

```bash
# 验证 tmux 会话
tmux ls

# 验证锁文件已清理
ls /tmp/ai_swarm/locks/

# 运行系统自检
./scripts/swarm_selfcheck.sh
```

---

## 维护清单

定期维护检查项：

- [ ] **tmux 清理**：检查并关闭残留会话
  ```bash
  tmux ls | grep '^swarm-' || echo "无残留会话"
  ```

- [ ] **状态目录清理**：检查 locks/ 和 status.log
  ```bash
  ls -la /tmp/ai_swarm/
  ```

- [ ] **重建流程**：必要时重新初始化环境
  ```bash
  rm -rf /tmp/ai_swarm/* && mkdir -p /tmp/ai_swarm/locks
  ```

- [ ] **脚本健康检查**：验证所有脚本可执行
  ```bash
  ./scripts/swarm_selfcheck.sh
  ```

- [ ] **配置验证**：检查 _config.sh 和 _common.sh
  ```bash
  source scripts/_config.sh && echo "SWARM_STATE_DIR=$SWARM_STATE_DIR"
  ```

---

## 最佳实践

### 定期维护建议

1. **每周检查**：运行 `swarm selfcheck` 验证环境
2. **每月清理**：清理旧的状态备份和日志
3. **重大变更前**：执行五步紧急恢复流程的第一步（备份）

### 常见操作规范

1. **修改配置前**：备份状态目录
2. **重启服务前**：确保所有 Worker 正常停止
3. **处理锁问题**：优先检查锁文件状态，而非直接删除
4. **记录变更**：维护操作应记录在案

### 故障响应流程

```
发现问题
    |
    v
运行自检 ./scripts/swarm_selfcheck.sh
    |
    v
根据错误类型选择处理方式：
    - 配置问题 → 修复配置后重试
    - 锁问题 → 清理锁文件
    - 会话问题 → 重建会话
    - 严重故障 → 执行五步紧急恢复流程
    |
    v
验证恢复 ./scripts/swarm_selfcheck.sh
    |
    v
记录归档
```

---

## 相关文档

- [脚本索引](SCRIPTS.md) - 所有脚本用法
- [CHANGELOG.md](../CHANGELOG.md) - 版本历史
- [README.md](../README.md) - 项目主文档
