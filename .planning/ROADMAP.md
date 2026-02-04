# Roadmap: AI Swarm

## Milestones

- ✅ **v1.90** — 统一任务入口 CLI (Active)
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
<summary>✅ v1.88 一键启动配置 (SHIPPED 2026-02-04)</summary>

- [x] Phase 30: 文档更新 (1/1 plan)

**Delivered:** README.md 新增"快速启动"小节，一行命令即可在任意目录启动 5 窗格布局

**Key accomplishments:**
1. 默认 codex 命令已为 `codex --yolo` (v1.87 期间完成)
2. README.md 新增"快速启动"小节

**Stats:**
- 1 phase, 1 plan
- 7/7 verification criteria passed

</details>

<details>
<summary>✅ v1.89 测试重写 (SHIPPED 2026-02-04)</summary>

- [x] Phase 31: 测试重写 (1/1 plan)

**Delivered:** 重写 3 个测试文件，适配新的 AutoRescuer API

**Key accomplishments:**
1. test_auto_rescuer.py - 9 个测试（模式检测、冷却机制、配置）
2. test_auto_rescuer_patterns.py - 6 个测试（模式常量）
3. test_e2e_auto_rescue.py - 4 个测试（E2E 工作流）

**Stats:**
- 1 phase, 1 plan
- 19/19 tests passed

</details>

<details>
<summary>🔵 v1.90 统一任务入口 CLI (IN PROGRESS)</summary>

- [ ] Phase 32: CLI task 子命令实现 (1/1 plan)
- [ ] Phase 33: 文档更新 (1/1 plan)

**Goal:** 新增 `swarm task` 子命令，统一调用任务管理脚本

**Requirements mapped:**
- CLI-01, CLI-02, CLI-03, CLI-04, CLI-05, EXIT-01 → Phase 32
- DOCS-01, DOCS-02 → Phase 33

**Success Criteria:**

**Phase 32: CLI task 子命令实现**
1. `swarm task --help` 显示 task 子命令帮助
2. `swarm task claim <task_id> <worker>` 调用脚本并透传退出码
3. `swarm task done <task_id> <worker>` 调用脚本并透传退出码
4. `swarm task fail <task_id> <worker> <reason>` 调用脚本并透传退出码
5. `swarm task run <task_id> <worker> <command...>` 调用脚本并透传退出码

**Phase 33: 文档更新**
1. README.md 包含 swarm task 用法示例
2. docs/SCRIPTS.md 包含完整参数说明

</details>

<details>
<summary>✅ v1.87 强化指挥官可感知能力 (SHIPPED 2026-02-04)</summary>

- [x] Phase 27: 状态汇总表增强 (1/1 plan)
- [x] Phase 28: 自动救援策略可配置化 (2/2 plans)
- [x] Phase 29: 任务指派回执闭环 (1/1 plan)

**Key accomplishments:**
- 状态汇总表增强 (last_update, wait_for, error_streak)
- 自动救援策略可配置化 (ENABLED, ALLOW, BLOCK)
- 任务指派状态广播 (ASSIGNED → START → DONE/ERROR)

See: `.planning/milestones/v1.87-ROADMAP.md` for full details.

</details>

<details>
<summary>✅ v1.86 主控自动救援闭环 + 状态汇总表 (SHIPPED 2026-02-04)</summary>

- [x] Phase 24: Master 救援核心 (2 plans)
- [x] Phase 25: 状态汇总表 (1 plan)
- [x] Phase 26: 集成与配置 (1 plan)

**13/13 requirements complete**

</details>

---

_For detailed v1.86 scope, see `.planning/milestones/v1.86-ROADMAP.md`_

---

*Roadmap created: 2026-02-04*
*Last updated: 2026-02-04 after v1.90 milestone initialization*
