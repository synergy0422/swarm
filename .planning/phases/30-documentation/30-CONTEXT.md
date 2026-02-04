# Phase 30: 文档更新 - Context

**Gathered:** 2026-02-04
**Status:** Ready for planning

<domain>
## Phase Boundary

在 README.md 的"5 窗格布局"章节中添加一个"快速启动"小节，包含一行命令示例，让用户可以在 WSL 任意目录启动 5 窗格布局。

</domain>

<decisions>
## Implementation Decisions

### 文档位置
- README.md 的"5 窗格布局"章节内
- 新增"快速启动"小节（不是章节开头，不是参数表格之后）

### 命令格式
- 单行命令 + 简短说明
- 示例包含所有必要环境变量

### 命令内容
```bash
LLM_BASE_URL="http://127.0.0.1:15721" ANTHROPIC_API_KEY="dummy" SWARM_WORKDIR="$PWD" CODEX_CMD="codex --yolo" ./scripts/swarm_layout_5.sh --attach
```

### 简短说明要点
- 可在任意目录执行
- SWARM_WORKDIR="$PWD" 确保所有窗格在当前目录
- LLM_BASE_URL 配置本地代理
- CODEX_CMD 可覆盖（默认为 codex --yolo）

</decisions>

<specifics>
## Specific Ideas

无特殊引用 — 按标准文档模式添加即可。

</specifics>

<deferred>
## Deferred Ideas

无

</deferred>

---

*Phase: 30-documentation*
*Context gathered: 2026-02-04*
