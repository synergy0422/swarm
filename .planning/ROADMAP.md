# Roadmap: AI Swarm

## Milestones

- ✅ **v1.9** — 自然语言任务入口 (Active)
- ✅ **v1.90** — 统一任务入口 CLI (2026-02-05)
- ✅ **v1.89** — 测试重写 (2026-02-04) - Bug fix
- ✅ **v1.88** — 一键启动配置 (2026-02-04)
- ✅ **v1.87** — 强化指挥官可感知能力 (2026-02-04)
- ✅ **v1.86** — 主控自动救援闭环 + 状态汇总表 (2026-02-04)
- ✅ **v1.85** — Claude Tasks 集成 + 自动锁闭环 (2026-02-04)
- ✅ **v1.8** — 诊断快照 (2026-02-03)
- ✅ **v1.7** — 5 窗格布局 + Codex (2026-02-03)
- ✅ **v1.6** — 长期可维护性 + 流程闭环 (2026-02-03)
- ✅ **v1.5** — 维护性改进 (2026-02-02)
- ✅ **v1.4** — 共享状态与任务锁 (2026-02-02)
- ✅ **v1.3** — 通信协议 (2026-02-02)
- ✅ **v1.2** — Claude Code CLI 多窗口 (2026-02-01)
- ✅ **v1.1** — UAT & CLI 增强 (2026-02-01)
- ✅ **v1.0** — MVP (2026-01-31)

<details>
<summary>✅ v1.90 统一任务入口 CLI (SHIPPED 2026-02-05)</summary>

- [x] Phase 32: CLI task 子命令实现 (1/1 plan)
- [x] Phase 33: 文档更新 (1/1 plan)

**Delivered:** Unified `swarm task` subcommand for task management

**Key accomplishments:**
1. `swarm task claim/done/fail/run` commands implemented
2. Exit code passthrough from underlying scripts
3. Documentation updated in README.md and docs/SCRIPTS.md

**Stats:**
- 2 phases, 2 plans
- 7/7 requirements implemented
- 4/4 documentation requirements completed

</details>

<details>
<summary>🔵 v1.9 自然语言任务入口 (IN PROGRESS)</summary>

- [ ] Phase 34: FIFO 输入通道 + 指令解析 (1/1 plan) - 34-01-PLAN.md created
- [ ] Phase 35: 测试覆盖 (1/1 plan)
- [ ] Phase 36: 文档更新 (1/1 plan)

**Goal:** 支持通过 master 的 FIFO 输入通道发布自然语言任务，实现 tmux 后台运行时的任务派发

**Requirements mapped:**
- FIFO-01 ~ FIFO-06 → Phase 34
- CMD-01 ~ CMD-05 → Phase 34
- TASK-01 ~ TASK-04 → Phase 34
- CFG-01 → Phase 34
- CLI-01 ~ CLI-03 → Phase 34
- TEST-01 ~ TEST-03 → Phase 34
- TEST-04 ~ TEST-05 → Phase 35
- DOCS-01 ~ DOCS-04 → Phase 36

**Success Criteria:**

**Phase 34: FIFO 输入通道 + 指令解析**
1. `$AI_SWARM_DIR/master_inbox` FIFO 存在
2. master 非阻塞监听 FIFO（不挂起主循环）
3. `/task <prompt>` 创建 pending 任务
4. `/help` 输出指令说明
5. `/quit` 停止输入线程（主循环继续运行）
6. `swarm task add "<prompt>"` 向 FIFO 写入
7. 自然语言任务正确追加到 tasks.json
8. AI_SWARM_TASKS_FILE 环境变量被尊重

**Phase 35: 测试覆盖**
1. FIFO 输入新增 pending 任务（单元测试）
2. `/help` 输出正确（单元测试）
3. `/quit` 不影响主循环（单元测试）
4. master 运行时 FIFO 任务被 dispatcher 识别（集成测试）
5. 非交互模式不阻塞主循环（验证测试）

**Phase 36: 文档更新**
1. CHANGELOG.md 新增 V1.9 功能条目
2. README.md 包含自然语言发布任务用法
3. docs/SCRIPTS.md 包含 FIFO/CLI 命令说明
4. 兼容性与限制说明已记录

</details>

---

*Roadmap created: 2026-02-05*
*Last updated: 2026-02-05 after v1.9 milestone initialization*
