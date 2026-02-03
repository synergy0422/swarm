# Roadmap: AI Swarm v1.86

**Core Value:** 多 Agent 并行推进，Master 协调去重，减少人作为瓶颈

## Milestones

- ⏳ **v1.86** — 主控自动救援闭环 + 状态汇总表 (2026-02-04)
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

## v1.86 Phases

| # | Phase | Goal | Requirements | Success Criteria | Status |
|---|-------|------|--------------|------------------|--------|
| 24 | Master 救援核心 | 实现 Master 自动判断 WAIT/confirm 状态并安全确认 | RESCUE-01, RESCUE-02, RESCUE-03, RESCUE-04 | 6 | ✓ Complete |
| 25 | 状态汇总表 | 实现窗口状态汇总表输出 | RESCUE-05, RESCUE-06, RESCUE-07, RESCUE-08 | 4 | ✓ Complete (Verification) |
| 26 | 集成与配置 | 技术集成与配置项整理 | RESCUE-09, RESCUE-10, RESCUE-11, RESCUE-12, RESCUE-13 | 5 | Pending |

### Phase 24: Master 救援核心

**Goal:** 实现 Master 自动判断 WAIT/confirm/press-enter 状态，并执行安全确认

**Status:** Complete (2026-02-04)

**Requirements:**
- RESCUE-01: Master 扫描 tmux pane 输出时，自动判断 WAIT/confirm/press-enter 等等待状态
- RESCUE-02: 自动执行 send-keys Enter 进行安全确认
- RESCUE-03: 具备冷却时间（建议 30s/窗口），避免重复确认
- RESCUE-04: 严格白名单逻辑，不做危险操作（检测 rm -rf, DROP 等立即告警）

**Success Criteria:**
1. [x] Master 扫描 pane 时能识别 [WAIT], [confirm], [press enter] 等模式
2. [x] 检测到等待状态时自动发送 Enter
3. [x] 同一窗口 30s 内不重复确认（冷却机制）
4. [x] 检测到 rm -rf, DROP 等危险关键词时不自动确认
5. [x] 通过手测验证：模拟 WAIT 输出 → 验证 Enter 发送
6. [x] 不影响现有任务分发与锁机制

### Phase 25: 状态汇总表

**Goal:** 实现每轮扫描生成"窗口/状态/当前任务/备注"的简表

**Requirements:**
- RESCUE-05: 每次扫描生成一张"窗口/状态/当前任务/备注"的简表
- RESCUE-06: 与文档中"指挥官汇报格式"对齐
- RESCUE-07: 能区分 ERROR / WAIT / DONE / RUNNING 状态
- RESCUE-08: 状态优先级：ERROR > WAIT > RUNNING > DONE/IDLE

**Success Criteria:**
1. [x] 每轮扫描后输出状态汇总表
2. [x] 字段包含：window、state、task_id、note
3. [x] 状态优先级正确：ERROR > WAIT > RUNNING > DONE/IDLE
4. [x] 汇总表包含所有窗口的状态

**Status:** Complete (2026-02-04)

### Phase 26: 集成与配置

**Goal:** 复用现有组件，统一日志输出，配置项整理

**Requirements:**
- RESCUE-09: 复用 swarm/master.py 中的 PaneScanner 与 WaitDetector
- RESCUE-10: 复用 scripts/claude_auto_rescue.sh 的"安全确认"理念
- RESCUE-11: 统一走 swarm/status_broadcaster.py 输出状态日志
- RESCUE-12: 所有新增逻辑必须有清晰函数封装，避免在主循环里写过多内联逻辑
- RESCUE-13: 冷却时间、扫描频率可配置（用环境变量）

**Success Criteria:**
1. [ ] 复用现有 PaneScanner/WaitDetector，无重复代码
2. [ ] 复用 claude_auto_rescue.sh 的安全确认理念
3. [ ] 统一通过 status_broadcaster.py 输出日志
4. [ ] 新增逻辑有清晰函数封装，主循环简洁
5. [ ] 冷却时间、扫描频率可通过环境变量配置

---

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| RESCUE-01 | 24 | Complete |
| RESCUE-02 | 24 | Complete |
| RESCUE-03 | 24 | Complete |
| RESCUE-04 | 24 | Complete |
| RESCUE-05 | 25 | Complete |
| RESCUE-06 | 25 | Complete |
| RESCUE-07 | 25 | Complete |
| RESCUE-08 | 25 | Complete |
| RESCUE-09 | 26 | Pending |
| RESCUE-10 | 26 | Pending |
| RESCUE-11 | 26 | Pending |
| RESCUE-12 | 26 | Pending |
| RESCUE-13 | 26 | Pending |

**Coverage:**
- v1.86 requirements: 13 total
- Complete: 8 (RESCUE-01~08)
- Pending: 5 (RESCUE-09~13)

---

*Roadmap created: 2026-02-04*
*Last updated: 2026-02-04 after Phase 25 verification complete*
