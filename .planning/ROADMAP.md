# Roadmap: AI Swarm

**Defined:** 2026-01-31
**Core Value:** 多 Agent 并行推进，Master 协调去重，减少人作为瓶颈

## Milestones

- ✅ **v1.0 - v1.6** — Previous milestones archived in `.planning/milestones/`
- ✅ **v1.7** — 5 窗格布局 + Codex — [archived](milestones/v1.7-ROADMAP.md)
- ⏳ **v1.8** — 诊断快照 — Defining requirements

## v1.8 Phases

### Phase 23: 快照脚本实现

**Goal:** 实现 `scripts/swarm_snapshot.sh` 脚本

**Requirements:**
- SNAP-01 ~ SNAP-09 (快照脚本功能)

**Success Criteria:**
1. 脚本支持 `--session` / `--lines` / `--out` 参数
2. 脚本输出 tmux 结构信息到快照目录
3. 脚本捕获每个 pane 的最近 N 行输出
4. 脚本记录状态文件和锁目录（如存在）
5. 脚本记录 git 版本信息
6. 脚本不创建/修改任何状态文件

---

*For completed milestones, see `.planning/milestones/`*
