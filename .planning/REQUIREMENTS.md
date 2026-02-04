# Requirements: AI Swarm v1.88

**Defined:** 2026-02-04
**Core Value:** 多 Agent 并行推进，Master 协调去重，减少人作为瓶颈

## v1.88 Requirements

Requirements for "一键启动配置" milestone.

### Documentation

- [ ] **DOCS-01**: README.md 或 docs/SCRIPTS.md 添加一行命令启动示例

**Example format:**
```bash
LLM_BASE_URL="http://127.0.0.1:15721" ANTHROPIC_API_KEY="dummy" SWARM_WORKDIR="$PWD" CODEX_CMD="codex --yolo" ./scripts/swarm_layout_5.sh --attach
```

**Example requirements:**
- 包含 LLM_BASE_URL 配置
- 包含 SWARM_WORKDIR=$PWD（任意目录）
- 包含 CODEX_CMD="codex --yolo"
- 包含 --attach 参数
- 位于 README.md 或 docs/SCRIPTS.md

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| 新增 swarm 子命令 | 不改 CLI 架构 |
| Web/跨机器支持 | 不做 Web/跨机器 |
| 其他功能合并 | 范围严格限制 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| DOCS-01 | Phase 30 | Pending |

**Coverage:**
- v1.88 requirements: 1 total
- Mapped to phases: 1
- Unmapped: 0

---
*Requirements defined: 2026-02-04*
*Last updated: 2026-02-04 after milestone initialization*
