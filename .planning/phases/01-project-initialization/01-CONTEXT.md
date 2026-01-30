# Phase 1: 项目初始化 - Context

**Gathered:** 2026-01-31
**Status:** Ready for planning

<domain>
## Phase Boundary

复制 Phase 2 核心代码，搭建 MVP 目录结构，适配路径配置，验证测试套件。
- 复制 config.py、task_queue.py、worker_smart.py、tests/
- 适配为 MVP 目录结构
- 路径指向 /tmp/ai_swarm/
- pytest 能跑通
- 提供 smoke test 验证核心闭环

</domain>

<decisions>
## Implementation Decisions

### 目录结构
- `swarm/` — 核心 Python 模块（config、task_queue、worker、master、tmux_utils 等）
- `scripts/` — 启动脚本（init_tmux、run_master、run_worker）
- `tests/` — 保留并支持 pytest
- `README.md` — 最小使用说明
- `.env.example` — 环境变量模板（不提交 .env）

### 配置优先级
1. 环境变量（最高优先级）
2. `.env` 文件
3. `config.py` 默认值

### 共享状态目录
- 固定路径: `/tmp/ai_swarm/`
- 可通过环境变量 `AI_SWARM_BASE` 覆盖
- 目录结构: `/tmp/ai_swarm/{status.log, tasks.json, locks/, results/}`

### 敏感信息管理
- API Key 只从环境变量读取（`ANTHROPIC_API_KEY`、`OPENAI_API_KEY`）
- 不写入代码，不提交仓库
- `.env.example` 提供变量名模板

### 测试验证
- `pytest -q` 必须通过
- Smoke test: 启动 tmux session + 1 master + 3 worker
  - master 能发任务
  - worker 能回写结果
  - 验证完整闭环

</decisions>

<specifics>
## Specific Ideas

- "最小可运行"原则 — 不追求完美，先跑通
- 环境变量覆盖机制 — 方便部署和测试
- Smoke test 是核心验证标准

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-project-initialization*
*Context gathered: 2026-01-31*
