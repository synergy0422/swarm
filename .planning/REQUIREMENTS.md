# Requirements: AI Swarm v1.9

**Defined:** 2026-02-05
**Core Value:** 多 Agent 并行推进，Master 协调去重，减少人作为瓶颈

## v1.9 Requirements

Requirements for "自然语言任务入口" milestone.

### FIFO 输入通道

- [ ] **FIFO-01**: 创建 `$AI_SWARM_DIR/master_inbox` 命名管道
- [ ] **FIFO-02**: master 启动时确保 FIFO 存在
- [ ] **FIFO-03**: 非阻塞监听 FIFO（超时机制，不阻塞主循环）
- [ ] **FIFO-04**: 读取超时后返回空字符串而非阻塞
- [ ] **FIFO-05**: 输入线程可安全退出（/quit 仅停止输入线程，主循环不阻塞）
- [ ] **FIFO-06**: 默认行为仅在启用交互模式时生效（避免误触）

### 指令语法

- [ ] **CMD-01**: `/task <prompt>` — 解析并创建任务
- [ ] **CMD-02**: `/help` — 输出可用指令说明
- [ ] **CMD-03**: `/quit` — 终止输入线程（不影响主循环）
- [ ] **CMD-04**: 无前缀文本视为任务 prompt
- [ ] **CMD-05**: 空行忽略

### 任务管理

- [ ] **TASK-01**: 使用 `TaskQueue.add_task()` 追加任务（当前项目使用 add_task）
- [ ] **TASK-02**: task_id 基于当前最大 id 递增
- [ ] **TASK-03**: 任务格式与现有系统一致（status: pending）
- [ ] **TASK-04**: 原子写入 tasks.json

### 配置选项

- [ ] **CFG-01**: 尊重 `AI_SWARM_TASKS_FILE` 环境变量（任务文件可配置）

### CLI 辅助命令

- [ ] **CLI-01**: `swarm task add "<prompt>"` — 向 FIFO 写入文本
- [ ] **CLI-02**: 命令尊重 `AI_SWARM_DIR` 环境变量
- [ ] **CLI-03**: 新增命令兼容现有 `swarm task` 子命令解析（避免破坏现有命令）

### 测试 (TDD)

- [ ] **TEST-01**: FIFO 输入新增 pending 任务
- [ ] **TEST-02**: `/help` 指令输出正确
- [ ] **TEST-03**: `/quit` 不影响主循环
- [ ] **TEST-04**: master 运行时 FIFO 任务被 dispatcher 识别
- [ ] **TEST-05**: 非交互模式不阻塞主循环（确保 master 不挂）

### 文档

- [ ] **DOCS-01**: 更新 CHANGELOG.md 新增 V1.9 功能条目
- [ ] **DOCS-02**: 更新 README.md 自然语言发布任务用法
- [ ] **DOCS-03**: 更新 docs/SCRIPTS.md 新流程说明
- [ ] **DOCS-04**: 新增脚本/命令必须写入 docs/SCRIPTS.md

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| FIFO-01 | Phase 34 | Pending |
| FIFO-02 | Phase 34 | Pending |
| FIFO-03 | Phase 34 | Pending |
| FIFO-04 | Phase 34 | Pending |
| FIFO-05 | Phase 34 | Pending |
| FIFO-06 | Phase 34 | Pending |
| CMD-01 | Phase 34 | Pending |
| CMD-02 | Phase 34 | Pending |
| CMD-03 | Phase 34 | Pending |
| CMD-04 | Phase 34 | Pending |
| CMD-05 | Phase 34 | Pending |
| TASK-01 | Phase 34 | Pending |
| TASK-02 | Phase 34 | Pending |
| TASK-03 | Phase 34 | Pending |
| TASK-04 | Phase 34 | Pending |
| CFG-01 | Phase 34 | Pending |
| CLI-01 | Phase 34 | Pending |
| CLI-02 | Phase 34 | Pending |
| CLI-03 | Phase 34 | Pending |
| TEST-01 | Phase 34 | Pending |
| TEST-02 | Phase 34 | Pending |
| TEST-03 | Phase 34 | Pending |
| TEST-04 | Phase 35 | Pending |
| TEST-05 | Phase 35 | Pending |
| DOCS-01 | Phase 36 | Pending |
| DOCS-02 | Phase 36 | Pending |
| DOCS-03 | Phase 36 | Pending |
| DOCS-04 | Phase 36 | Pending |

**Coverage:**
- v1.9 requirements: 28 total
- Phase 34 (Implementation): 22 requirements
- Phase 35 (Testing): 5 requirements
- Phase 36 (Documentation): 4 requirements

---

*Requirements defined: 2026-02-05*
*Last updated: 2026-02-05 after requirements clarification*
