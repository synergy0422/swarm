# Requirements: AI Swarm v1.6

**Defined:** 2026-02-02
**Core Value:** 多 Agent 并行推进，Master 协调去重，减少人作为瓶颈

## v1.6 Requirements

### 统一配置 (CFGN)

- [ ] **CFGN-01**: 统一配置入口 — 新增 `scripts/_config.sh` 或 `swarm.env`，统一管理 SESSION_NAME / SWARM_STATE_DIR / WORKERS 列表 / LOG_LEVEL
- [ ] **CFGN-02**: 所有脚本统一读取配置 — `scripts/_common.sh` 和其他脚本 source `_config.sh` 获取配置

### 任务流程闭环 (WRAP)

- [ ] **WRAP-01**: 任务流程包装脚本 — 新增 `scripts/swarm_task_wrap.sh`，实现: acquire lock → write START → execute → write DONE/ERROR → release
- [ ] **WRAP-02**: 失败场景处理 — acquire 失败时写 SKIP/WAIT 状态，锁释放机制

### 自检与文档 (CHK)

- [ ] **CHK-01**: 一键自检脚本 — 新增 `scripts/swarm_selfcheck.sh`，检查 tmux 可用性、脚本可执行性、配置可读性

### 维护与扩展 (DOCS)

- [ ] **DOCS-03**: 更新 README — 精简入口，导航链接到 MAINTENANCE.md / SCRIPTS.md / CHANGELOG.md
- [ ] **DOCS-04**: 创建 docs/MAINTENANCE.md — 环境恢复、故障排查、紧急流程、维护清单
- [ ] **DOCS-05**: 创建 docs/SCRIPTS.md — 完整脚本索引 (用途/参数/示例)
- [ ] **DOCS-06**: 创建 CHANGELOG.md — v1.0-v1.6 变更摘要

## v2 Requirements

Deferred to future release.

### 状态面板 (UI)

- **UI-01**: Web 状态面板 — 实时显示所有 Worker 状态
- **UI-02**: 可视化任务流程 — 展示任务流转状态

### 流水线模式 (PIPE)

- **PIPE-01**: 任务流水线 — Worker 按流水线方式协作
- **PIPE-02**: 依赖管理 — 任务间依赖关系定义

### 对等模式 (P2P)

- **P2P-01**: 对等协作 — Worker 之间直接通信
- **P2P-02**: 去中心化协调 — 无 Master 的任务分配

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Web/UI 界面 | 留到 v1.7 |
| P2P/对等模式 | 复杂度高，后续版本 |
| Pipeline/流水线 | 后续版本 |
| 修改 swarm/*.py | 除非必要，否则不碰 |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| **v1.6 Active** | | |
| CFGN-01 | Phase 18 | Complete | |
| CFGN-02 | Phase 18 | Complete | |
| WRAP-01 | Phase 19 | Complete | |
| WRAP-02 | Phase 19 | Complete | |
| CHK-01 | Phase 20 | Pending |
| DOCS-03 | Phase 21 | Pending |
| DOCS-04 | Phase 21 | Pending |
| DOCS-05 | Phase 21 | Pending |
| DOCS-06 | Phase 21 | Pending |

**Coverage:**
- v1.6 requirements: 10 total
- Mapped to phases: 10
- Unmapped: 0 ✓

---

*Requirements defined: 2026-02-02*
*Last updated: 2026-02-02 after v1.6 milestone start*
