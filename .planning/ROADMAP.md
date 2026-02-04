# Roadmap: AI Swarm

## Milestones

- ⏳ **v1.88** — 一键启动配置 (2026-02-04)
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
<summary>⏳ v1.88 一键启动配置 (2026-02-04)</summary>

- [ ] Phase 30: 文档更新 — 添加一键启动命令示例 (1/1 plan)

**Goal:** 文档添加一行命令启动示例

**Requirements:** DOCS-01

**Success Criteria:**
1. README.md 或 docs/SCRIPTS.md 包含完整一行命令示例
2. 示例命令可在任意目录执行
3. 包含 LLM_BASE_URL、SWARM_WORKDIR=$PWD、CODEX_CMD、--attach

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
*Last updated: 2026-02-04 after v1.88 milestone initialization*
