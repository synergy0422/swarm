# Roadmap: AI Swarm

**Defined:** 2026-01-31
**Core Value:** 多 Agent 并行推进，Master 协调去重，减少人作为瓶颈

## Milestones

- ✅ **v1.5** — 状态广播闭环 + 自动救援 + 维护性改进 (Phases 15-17, shipped 2026-02-02)
- 🚧 **v1.6** — 长期可维护性 + 流程闭环 (Phases 18-20) ← Current
- 📋 **v1.7+** — UI 面板、P2P/流水线模式 (待规划)

## v1.6 Phases

**Goal:** 提升系统可维护性，闭环任务流程，完善自检与文档

**约束：**
- 只做维护性与流程闭环
- 不做 UI/布局 (留到 v1.7)
- 不做 P2P/流水线/Web
- 不改 swarm/*.py (若必须改, 需说明理由)

### Phase 18: 统一配置入口

**Goal:** 创建统一配置入口，所有脚本集中读取配置

**Dependencies:** None (foundational phase)

**Requirements:** CFGN-01, CFGN-02

**Success Criteria:**

1. `scripts/_config.sh` 或 `swarm.env` 存在且可读
2. 配置项完整: SESSION_NAME, SWARM_STATE_DIR, WORKERS 列表, LOG_LEVEL
3. `_common.sh` source `_config.sh` 获取配置
4. 所有脚本通过 `_common.sh` 间接读取配置
5. 支持环境变量覆盖默认配置

---

### Phase 19: 任务流程闭环

**Goal:** 实现任务全生命周期包装，集成锁与状态

**Dependencies:** Phase 18 (统一配置入口)

**Requirements:** WRAP-01, WRAP-02

**Success Criteria:**

1. `scripts/swarm_task_wrap.sh` 存在且可执行
2. 完整流程: acquire lock → write START → execute → write DONE/ERROR → release
3. 失败处理: acquire 失败时写 SKIP/WAIT 状态
4. 锁释放机制正确 (只释放自己获取的锁)
5. 状态写入使用 `swarm_status_log.sh append`
6. 锁操作使用 `swarm_lock.sh`

---

### Phase 20: 自检与文档

**Goal:** 一键自检脚本 + 更新维护文档

**Dependencies:** Phase 18 (配置入口), Phase 19 (流程脚本)

**Requirements:** CHK-01, DOCS-03, DOCS-04

**Success Criteria:**

1. `scripts/swarm_selfcheck.sh` 存在且可执行
2. 自检覆盖: tmux 可用性, 脚本可执行性, 配置可读性
3. 自检输出清晰: 通过/失败项, 修复建议
4. README 更新: 脚本总表, 常见问题, 恢复流程
5. CONTRIBUTING 更新: 恢复流程, 维护指南

---

## v1.5 Phases (Archived)

<details>
<summary>✅ v1.5 维护性改进 (Phases 15-17) — SHIPPED 2026-02-02</summary>

- [x] Phase 15: _common.sh (1/1 plan) — completed 2026-02-02
- [x] Phase 16: Auto-Rescue (1/1 plan) — completed 2026-02-02
- [x] Phase 17: Status Broadcast (1/1 plan) — completed 2026-02-02

</details>

---

*Roadmap updated: 2026-02-02 after v1.5 milestone*
