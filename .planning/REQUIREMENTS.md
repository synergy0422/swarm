# Requirements: AI Swarm v1.7

**Defined:** 2026-02-03
**Core Value:** 多 Agent 并行推进，Master 协调去重，减少人作为瓶颈

## v1.7 Requirements

Requirements for 5 窗格布局 + Codex milestone. Single phase (22).

### Layout

- [x] **LAYOUT-01**: 5 窗格布局脚本 — 创建 `scripts/swarm_layout_5.sh`，支持：
  - 单 tmux window 内 5 个窗格（panes）
  - 左侧 2 窗格上下 50/50（master + codex）
  - 右侧 3 窗格等分（worker-0 + worker-1 + worker-2）
  - 默认 Codex 启动命令: `codex --yolo`
  - 参数支持: --session, --workdir, --left-ratio, --codex-cmd
  - 环境变量支持: CLAUDE_SESSION, SWARM_WORKDIR, CODEX_CMD
  - 继承 `_config.sh`/`_common.sh` 配置

- [x] **LAYOUT-02**: 文档更新 — 更新以下文档：
  - README.md: 新增"5 窗格布局"章节，说明和示例
  - docs/SCRIPTS.md: 补充 swarm_layout_5.sh 完整文档
  - docs/SCRIPTS.md 或 docs/MAINTENANCE.md: 说明如何修改布局比例和 codex 命令

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| 修改 swarm/*.py | v1.7 仅新增脚本，不改 Python 代码 |
| Web 状态面板 | 延期到 v1.7+ 或更晚 |
| P2P/流水线模式 | 延期到 v1.7+ 或更晚 |
| 复杂右分割 (--right-split > 3) | 默认 3 等分，暂不支持复杂分割 |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| LAYOUT-01 | Phase 22 | Complete | |
| LAYOUT-02 | Phase 22 | Complete | |

**Coverage:**
- v1.7 requirements: 2 total
- Mapped to phases: 2
- Unmapped: 0

---

*Requirements defined: 2026-02-03*
*Last updated: 2026-02-03 after v1.7 milestone started*
