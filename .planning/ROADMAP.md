# Roadmap: AI Swarm

## Milestones

- ⏳ **v1.87** — 强化指挥官可感知能力

### Phase 27: 状态汇总表增强

**Goal:** 增强状态汇总表，新增 last_update / wait_for / error_streak 字段，提升指挥官感知能力

**Depends on:** Phase 26

**Plans:** 1 plan

Plans:
- [x] 27-01-PLAN.md: 状态汇总表增强实现

**Details:**

### Phase 27: 状态汇总表增强

**验收标准:**
- [ ] 状态汇总表包含新增 3 个字段（last_update, wait_for, error_streak）
- [ ] WAIT 时长准确累计
- [ ] ERROR 连续次数正确计数
- [ ] 输出格式仍在 stdout（非 UI）

**技术路径:**
- 复用 PaneSummary 增加字段：last_update_ts, wait_since_ts, error_streak
- 状态变化时维护时间戳
- 进入 WAIT 时记录 wait_since_ts
- 进入 ERROR 时 error_streak += 1，其他状态重置为 0
- 汇总表格式化时显示：last_update 为 YYYY-MM-DD HH:MM:SS 或 ago
- wait_for 显示持续等待时长（秒或分钟）

---

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
<summary>✅ v1.86 主控自动救援闭环 + 状态汇总表 (SHIPPED 2026-02-04)</summary>

- [x] Phase 24: Master 救援核心 (2 plans) — AutoRescuer + Bug Fixes
- [x] Phase 25: 状态汇总表 (1 plan) — Verification passed
- [x] Phase 26: 集成与配置 (1 plan) — 验证通过

**13/13 requirements complete**

</details>

---

_For detailed v1.86 scope, see `.planning/milestones/v1.86-ROADMAP.md`_

---

*Roadmap created: 2026-02-04*
*Last updated: 2026-02-04 after v1.86 milestone completion*
