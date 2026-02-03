# Roadmap: AI Swarm

**Defined:** 2026-01-31
**Core Value:** 多 Agent 并行推进，Master 协调去重，减少人作为瓶颈

## Milestones

- ✅ **v1.0 - v1.6** — Previous milestones archived in `.planning/milestones/`
- 📋 **v1.7** — 5 窗格布局 + Codex (Phase 22, planning pending)
- ⏳ **v1.7+** — UI 面板、P2P/流水线模式 (待规划)

## v1.7 Roadmap

**Goal:** 5 窗格布局 + Codex 集成

### Plans

| # | Plan | Objective |
|---|------|-----------|
| 22-01 | 5 窗格布局脚本 | 创建 `scripts/swarm_layout_5.sh` 和文档 |

### Phase 22-01: 5 窗格布局脚本

**Requirements covered:** LAYOUT-01, LAYOUT-02

**Success criteria:**
1. `scripts/swarm_layout_5.sh` 可执行
2. 单 tmux window 内 5 个窗格（panes）
3. 左侧 master/codex 上下 50/50
4. 右侧 worker-0/1/2 等分
5. `tmux list-panes -t <session>:0` 显示 5 个窗格
6. Codex 窗口运行 `codex --yolo`
7. 参数和环境变量生效
8. README.md 新增"5 窗格布局"说明
9. docs/SCRIPTS.md 补充完整文档

---

*Roadmap created: 2026-02-03*
*Last updated: 2026-02-03 after v1.7 milestone started*
