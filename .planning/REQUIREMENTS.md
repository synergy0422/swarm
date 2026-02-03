# Requirements: AI Swarm v1.8 诊断快照

**Defined:** 2026-02-03
**Core Value:** 多 Agent 并行推进，Master 协调去重，减少人作为瓶颈

## v1.8 Requirements

### 快照脚本

- [x] **SNAP-01**: 脚本支持 `--session` / `CLAUDE_SESSION` 参数指定 tmux 会话
- [x] **SNAP-02**: 脚本支持 `--lines` / `SNAPSHOT_LINES` 参数配置输出行数（默认 50）
- [x] **SNAP-03**: 脚本支持 `--out` / `SNAPSHOT_DIR` 参数指定输出目录（默认 `/tmp/ai_swarm_snapshot_<timestamp>`）
- [x] **SNAP-04**: 脚本输出 tmux 结构信息（sessions/windows/panes）
- [x] **SNAP-05**: 脚本捕获每个 pane 的最近 N 行输出
- [x] **SNAP-06**: 脚本记录状态文件（`$SWARM_STATE_DIR/status.log`）内容（若存在）
- [x] **SNAP-07**: 脚本记录锁目录（`$SWARM_STATE_DIR/locks/`）列表（若存在）
- [x] **SNAP-08**: 脚本记录关键脚本版本信息（`git rev-parse --short HEAD`）
- [x] **SNAP-09**: 脚本为只读操作，不创建/修改任何状态文件

### 文档

- [x] **DOCS-01**: README.md 新增"诊断快照"使用说明
- [x] **DOCS-02**: docs/SCRIPTS.md 增加 swarm_snapshot.sh 完整文档

## Out of Scope

| Feature | Reason |
|---------|--------|
| 自动压缩快照 | 非核心需求，手动 gzip 即可 |
| 远程快照上传 | 超出诊断工具范畴 |
| 快照对比功能 | 可用 diff 工具手动比较 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| SNAP-01 | 23 | Complete |
| SNAP-02 | 23 | Complete |
| SNAP-03 | 23 | Complete |
| SNAP-04 | 23 | Complete |
| SNAP-05 | 23 | Complete |
| SNAP-06 | 23 | Complete |
| SNAP-07 | 23 | Complete |
| SNAP-08 | 23 | Complete |
| SNAP-09 | 23 | Complete |
| DOCS-01 | 23 | Complete |
| DOCS-02 | 23 | Complete |

**Coverage:**
- v1.8 requirements: 11 total
- Mapped to phases: 11
- Unmapped: 0 ✓

---

*Requirements defined: 2026-02-03*
*Last updated: 2026-02-03 after v1.8 milestone start*
