# Changelog

## v1.6 (2026-02-XX) - 长期可维护性 + 流程闭环

**Delivered:** Phase 18 统一配置入口、Phase 20 自检

**Planned:** Phase 19 任务包装、Phase 21 维护文档

### Features

- 新增 _config.sh 统一配置管理 (Phase 18)
- 新增 swarm_task_wrap.sh 任务生命周期包装器 (Phase 19)
- 新增 swarm_selfcheck.sh 一键系统自检 (Phase 20)

### Under the Hood

- 新增 docs/MAINTENANCE.md 维护指南 (Phase 21)
- 新增 docs/SCRIPTS.md 脚本索引 (Phase 21)
- 新增 CHANGELOG.md 版本历史 (Phase 21)

---

## v1.5 (2026-02-02) - 状态广播闭环 + 自动救援 + 维护性改进

**Delivered:** _common.sh、claude_auto_rescue.sh、swarm_broadcast.sh

### Features

- 新增 claude_auto_rescue.sh 自动确认脚本
- 新增 swarm_broadcast.sh 状态广播

### Under the Hood

- 新增 _common.sh 统一配置和日志
- 更新 CONTRIBUTING.md

---

## v1.4 (2026-02-02) - 状态日志 + 锁机制

**Delivered:** swarm_status_log.sh、swarm_lock.sh、状态日志与锁机制

### Features

- 新增 swarm_status_log.sh 状态日志记录
- 新增 swarm_lock.sh 任务锁管理
- 实现原子锁获取（Python O_CREAT|O_EXCL）
- JSON Lines 格式的状态日志

### Under the Hood

- lock 文件格式：task_id, worker, acquired_at, expires_at
- 支持可选 TTL（不过期时为 null）

---

## v1.3 (2026-02-02) - Claude Code 通信协议

**Delivered:** Claude CLI 通信脚本套件、[TASK]/[ACK]/[DONE] 协议

### Features

- 新增 claude_comm.sh 通信命令（send/send-raw/poll/status）
- 新增 claude_poll.sh 持续监控
- 新增 claude_status.sh 快速状态检查
- 实现 [TASK]/[ACK]/[DONE]/[ERROR]/[WAIT]/[HELP] 协议标记

### Bug Fixes

- 多行发送修复为单行发送（防止 Claude 误解析部分消息）
- 添加 send-raw 命令用于协议设置消息

### Under the Hood

- 单行任务发送
- 行首标记匹配（tail -1）

---

## v1.2 (2026-02-01) - Claude Code CLI 多窗口

**Delivered:** 4 tmux 窗口 + Claude CLI 运行

### Features

- 新增 run_claude_swarm.sh 启动脚本
- 4 窗口启动：master + worker-0/1/2
- --attach/--no-attach 挂载选项
- --workdir/-d 工作目录覆盖

### Under the Hood

- Session 命名：swarm-claude-default
- Claude CLI 可用性检查

---

## v1.1 (2026-02-01) - UAT 与 CLI 增强

**Delivered:** CLI 状态增强、UAT 验证

### Features

- 新增 `swarm status --panes` 窗口快照显示
- 状态图标：[ERROR]/[DONE]/[ ] 可视化
- 20 行内容限制（防止终端溢出）

### Under the Hood

- 更新 LLM_BASE_URL 配置文档
- 完成 8 步 UAT 测试

---

## v1.0 (2026-01-31) - MVP 多代理协作系统

**Delivered:** 完整多代理协作系统 + tmux 集成

### Features

- Master-Worker 架构
- tmux 会话管理
- 任务队列与分发
- 自动救援机制
- 成本跟踪

### Scripts

- swarm CLI 命令行工具
- run_swarm.sh 启动脚本

### Under the Hood

- 207 测试用例通过
- 14 个 Python 源文件
- 4,315 行 Python 代码
